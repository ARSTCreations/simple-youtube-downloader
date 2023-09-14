import tkinter as tk
from tkinter import filedialog, messagebox, StringVar
from moviepy.editor import VideoFileClip, AudioFileClip
from pytube import YouTube
from proglog import ProgressBarLogger
import os
import threading
import webbrowser

temp_path = os.path.expanduser("~\AppData\Local\Temp")
if not os.access(temp_path, os.W_OK):
    messagebox.showerror("Error", "Got no permission on the Temp folder.")
    exit()

def select_save_path():
    selected_path = filedialog.askdirectory()
    if selected_path:
        save_path_entry.delete(0, tk.END)
        save_path_entry.insert(0, selected_path)

def download_video():
    video_url = url_entry.get()
    save_path = save_path_entry.get()

    if not os.path.exists(save_path):
        messagebox.showerror("Error", "The specified save path does not exist.")
        return

    def download_progress_callback(stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = (bytes_downloaded / total_size) * 100
        # print(f"Downloaded {bytes_downloaded} bytes out of {total_size} bytes ({percentage:.2f}%)")
        percentage_string_var.set(f"Downloaded {(bytes_downloaded/1000000):.2f}/{(total_size/1000000):.2f}MB ({percentage:.2f}%)")
        # print(f"Downloading {(bytes_downloaded/1000000):.2f}/{(total_size/1000000):.2f}MB ({percentage:.2f}%)")

    class convert_progress_callback(ProgressBarLogger):
        def callback(self, **changes):
            # Every time the logger message is updated, this function is called with
            # the `changes` dictionary of the form `parameter: new value`.
            for (parameter, value) in changes.items():
                # print('Parameter %s is now %s' % (parameter, value))
                percentage_string_var.set('Parameter %s is now %s' % (parameter, value))
        
        def bars_callback(self, bar, attr, value, old_value=None):
            # Every time the logger progress is updated, this function is called        
            percentage = (value / self.bars[bar]['total']) * 100
            # print(f"Converting {percentage:.2f}%")
            percentage_string_var.set(f"Converting {percentage:.2f}%")

    proglogger = convert_progress_callback()

    def adaptive_res_thread():
        try:
            percentage_string_var.set("Connecting...")
            download_button.config(state=tk.DISABLED)
            select_path_button.config(state=tk.DISABLED)
            
            status_string_var.set("Downloading Adaptive Video")
            ytvid = YouTube(video_url, on_progress_callback=download_progress_callback)
            video_file = ytvid.streams.filter(progressive=False).order_by("resolution")
            print("a")
            if not any("1080p" in quality.resolution for quality in video_file):
                messagebox.showerror("Invalid", "It seems that the video quality is not available.")
                percentage_string_var.set("Ready")
                status_string_var.set("")
                download_button.config(state=tk.NORMAL)
                select_path_button.config(state=tk.NORMAL)
                return
            if radio_resolution.get() == "ultra_res":
                print("b")
                video_file = video_file.last()
            else:
                print("c")
                video_file = ytvid.streams.filter(progressive=False, resolution="1080p").first()
            # video_file.download(save_path)
            video_file.download(temp_path)
            
            default_path = os.path.join(temp_path, video_file.default_filename)
            print(default_path)
            new_vid_path = os.path.join(temp_path, "video"+video_file.default_filename)
            print(new_vid_path)
            if os.path.exists(new_vid_path):
                os.remove(new_vid_path)
            os.rename(default_path, new_vid_path)
            
            status_string_var.set("Downloading Adaptive Audio")
            ytaud = YouTube(video_url, on_progress_callback=download_progress_callback)
            audio_file = ytaud.streams.filter(only_audio=True).first()
            audio_file.download(temp_path)
            
            default_path = os.path.join(temp_path, audio_file.default_filename)
            new_aud_path = os.path.join(temp_path, "audio"+audio_file.default_filename+".mp3")
            if os.path.exists(new_aud_path):
                os.remove(new_aud_path)
            os.rename(default_path, new_aud_path)
        
        except Exception as e:
            messagebox.showerror("Invalid", "It seems that the link is invalid.")
            print(e)
        
        try:
            # combine video audio
            status_string_var.set("Combining Hi-Res Video and Audio...")
            video_clip = VideoFileClip(new_vid_path)
            audio_clip = AudioFileClip(new_aud_path)

            final_clip = video_clip.set_audio(audio_clip)
            if os.path.exists(str(save_path)+"/"+video_file.default_filename+".mp4"):
                os.remove(str(save_path)+"/"+video_file.default_filename+".mp4")

            if (radio_encoder.get()):
                try:
                    print("Trying hevc_amf")
                    status_string_var.set("Combining Hi-Res Video and Audio... (Using hevc_amf)")
                    final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="hevc_amf")
                except:
                    pass
                try:
                    print("Nope.., Trying hevc_nvenc")
                    status_string_var.set("Combining Hi-Res Video and Audio... (Using hevc_nvenc)")
                    # final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="hevc_nvenc", ffmpeg_params=["-c:v", "hevc_nvenc", "-b:v", "5M", "-threads", "auto", "-hwaccel", "auto", ])
                    final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="hevc_nvenc")
                except:
                    pass
                try:
                    print("Nope.., Trying hevc_qsv")
                    status_string_var.set("Combining Hi-Res Video and Audio... (Using hevc_qsv)")
                    final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="hevc_qsv")
                except:
                    print("Nope.., Falling back to libx264")
                    status_string_var.set("Combining Hi-Res Video and Audio... (No hardware support, using libx265)")
                    final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="libx265")
            else:
                status_string_var.set("Combining Hi-Res Video and Audio... (Using libx265)")
                final_clip.write_videofile(str(save_path)+"/"+video_file.default_filename+".mp4", fps=video_clip.fps, logger=proglogger, codec="libx265")
            audio_clip.close()
            video_clip.close()
            # delete video and audio
            if os.path.exists(new_vid_path) and os.path.exists(new_aud_path):
                os.remove(new_vid_path)
                os.remove(new_aud_path)
            download_button.config(state=tk.NORMAL)
            download_button.config(state=tk.NORMAL)
            percentage_string_var.set("Ready")
            status_string_var.set("")
            messagebox.showinfo("Download Complete", "Video downloaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", "Failed to combine video and audio.")
            print(e)

    def progressive_res_thread():
        try:
            percentage_string_var.set("Connecting...")
            download_button.config(state=tk.DISABLED)
            select_path_button.config(state=tk.DISABLED)
            
            status_string_var.set("Downloading Progressive Video")
            ytvid = YouTube(video_url, on_progress_callback=download_progress_callback)
            video_file = ytvid.streams.filter(progressive=True).order_by("resolution").last()
            video_file.download(save_path)
        except Exception as e:
            messagebox.showerror("Invalid", "It seems that the link is invalid.")
            print(e)
        finally:
            download_button.config(state=tk.NORMAL)
            download_button.config(state=tk.NORMAL)
            percentage_string_var.set("Ready")
            status_string_var.set("")
            messagebox.showinfo("Download Complete", "Video downloaded successfully!")

    # Create a separate thread for downloading
    download_thread = threading.Thread(target=adaptive_res_thread if radio_resolution.get() == "ultra_res" or radio_resolution.get() == "hi_end_res" else progressive_res_thread)
    download_thread.start()


# Create a Tkinter window
root = tk.Tk()
root.title("YouTube Video Downloader")
root.iconbitmap("assets/icon.ico")
root.config(bg="#26242f")

# set the size of the window
root.geometry("480x720")

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Banner Image
banner_image = tk.PhotoImage(file="assets/banner.png")
banner_label = tk.Label(root, image=banner_image)
banner_label.pack()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

def callback(url):
   webbrowser.open_new_tab(url)

# Add a label and an entry field for the video URL
link = tk.Label(root, text="visit: github.com/ARSTCreations", fg="white", bg="#26242f")
link.pack()
link.bind("<Button-1>", lambda e:
callback("https://github.com/ARSTCreations"))

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Add a label and an entry field for the video URL
url_label = tk.Label(root, text="Enter Video URL:", fg="white", bg="#26242f")
url_label.pack()
url_entry = tk.Entry(root, width=50, fg="white", bg="#26242f")
# url_entry.insert(0, "https://www.youtube.com/watch?v=WO2b03Zdu4Q")
url_entry.pack()

def toggle_encoder_radio():
    if radio_resolution.get() == "high_res":
        radio_encoder_button1.config(state=tk.DISABLED)
        radio_encoder_button2.config(state=tk.DISABLED)
    else:
        radio_encoder_button1.config(state=tk.NORMAL)
        radio_encoder_button2.config(state=tk.NORMAL)

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()


# Resolution Selector
radio_resolution = tk.StringVar()
radio_resolution.set("high_res")
radio_resolution_label = tk.Label(root, text="Resolution:", fg="white", bg="#26242f")
radio_resolution_button1 = tk.Radiobutton(root, text="High", variable=radio_resolution, value="high_res", selectcolor="#26242f", highlightbackground="#26242f", highlightcolor="#26242f", fg="white", bg="#26242f", command=toggle_encoder_radio)
radio_resolution_button2 = tk.Radiobutton(root, text="Hi-End", variable=radio_resolution, value="hi_end_res", selectcolor="#26242f", highlightbackground="#26242f", highlightcolor="#26242f", fg="white", bg="#26242f", command=toggle_encoder_radio)
radio_resolution_button3 = tk.Radiobutton(root, text="Ultra", variable=radio_resolution, value="ultra_res", selectcolor="#26242f", highlightbackground="#26242f", highlightcolor="#26242f", fg="white", bg="#26242f", command=toggle_encoder_radio)
radio_resolution_label.pack()
radio_resolution_button1.pack()
radio_resolution_button2.pack()
radio_resolution_button3.pack()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Encoder Selector
radio_encoder = tk.BooleanVar()
radio_encoder.set(True)
radio_encoder_label = tk.Label(root, text="Encoder:", fg="white", bg="#26242f")
radio_encoder_button1 = tk.Radiobutton(root, text="Hardware (Performance)", variable=radio_encoder, value=True, selectcolor="#26242f", highlightbackground="#26242f", highlightcolor="#26242f", fg="white", bg="#26242f")
radio_encoder_button2 = tk.Radiobutton(root, text="Software (Quality)", variable=radio_encoder, value=False, selectcolor="#26242f", highlightbackground="#26242f", highlightcolor="#26242f", fg="white", bg="#26242f")
radio_encoder_label.pack()
radio_encoder_button1.pack()
radio_encoder_button2.pack()
radio_encoder_button2.select()
toggle_encoder_radio()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()


# Add a label and an entry field for the save path
save_path_label = tk.Label(root, text="Save Path:", fg="white", bg="#26242f")
save_path_label.pack()
default_save_path = os.path.expanduser("~\Desktop")
save_path_entry = tk.Entry(root, width=50, fg="white", bg="#26242f")
save_path_entry.insert(0, default_save_path)
save_path_entry.pack()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Add a button to select the save path
select_path_button = tk.Button(root, text="Select Path", command=select_save_path)
select_path_button.pack()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Add a download button
download_button = tk.Button(root, text="Download", command=download_video)
download_button.pack()

# Spacer
spacer = tk.Label(root, text="", fg="#26242f", bg="#26242f")
spacer.pack()

# Progress bar of download
percentage_string_var = StringVar()
status_string_var = StringVar()
percentage_string_var.set("Ready")
status_string_var.set("")
progress_bar = tk.Label(root, textvariable=percentage_string_var, fg="white", bg="#26242f")
status_text = tk.Label(root, textvariable=status_string_var, fg="white", bg="#26242f")
progress_bar.pack()
status_text.pack()

# Start the Tkinter main loop
root.mainloop()
