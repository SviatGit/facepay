import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import os
import numpy as np

from dotenv import load_dotenv

from face_utils import get_face_embedding, match_face
from user_store import load_users, register_user
import backend_api

load_dotenv()

USERS = load_users()
CAP = cv2.VideoCapture(0)

KNOWN_FACES_DIR = "known_faces"
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

def save_face_image(user_id, frame):
    path = os.path.join(KNOWN_FACES_DIR, f"{user_id}.jpg")
    cv2.imwrite(path, frame)

class FacePayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FacePay - Register & Send")

        self.face_embedding = None
        self.face_verified = False
        self.sender_id = None
        self.captured_frame = None

        self.setup_ui()
        self.update_video_feed()

    def setup_ui(self):
        notebook = ttk.Notebook(self.root)

        self.register_tab = ttk.Frame(notebook)
        self.payment_tab = ttk.Frame(notebook)

        notebook.add(self.register_tab, text="🧍 Register")
        notebook.add(self.payment_tab, text="💸 Send Payment")
        notebook.pack(expand=True, fill="both")

        self.build_register_tab()
        self.build_payment_tab()

    # --------- REGISTER TAB -----------
    def build_register_tab(self):
        tk.Label(self.register_tab, text="Stripe Customer ID (your own)").pack(pady=5)
        self.reg_stripe_id = tk.Entry(self.register_tab)
        self.reg_stripe_id.pack()

        tk.Label(self.register_tab, text="Full Name").pack(pady=5)
        self.reg_name = tk.Entry(self.register_tab)
        self.reg_name.pack()

        self.reg_video_label = tk.Label(self.register_tab)
        self.reg_video_label.pack(pady=10)

        self.capture_button = tk.Button(self.register_tab, text="📸 Capture Face", command=self.capture_face_for_register)
        self.capture_button.pack(pady=5)

        self.register_status = tk.Label(self.register_tab, text="", fg="green")
        self.register_status.pack()

        self.register_button = tk.Button(self.register_tab, text="✅ Register User", command=self.register_user, state=tk.DISABLED)
        self.register_button.pack(pady=10)

    def capture_face_for_register(self):
        ret, frame = CAP.read()
        if not ret:
            messagebox.showerror("Error", "Failed to capture frame.")
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            self.face_embedding = get_face_embedding(frame_rgb)
            self.captured_frame = frame.copy()
            self.register_status.config(text="✅ Face captured successfully", fg="green")
            self.register_button.config(state=tk.NORMAL)
        except Exception as e:
            self.register_status.config(text="❌ Face not found or multiple faces", fg="red")
            print("Face embedding error:", e)
            self.face_embedding = None
            self.captured_frame = None
            self.register_button.config(state=tk.DISABLED)

    def register_user(self):
        stripe_customer_id = self.reg_stripe_id.get().strip()
        name = self.reg_name.get().strip()

        if not all([stripe_customer_id, name, self.face_embedding, self.captured_frame is not None]):
            messagebox.showerror("Error", "Fill all fields and capture your face.")
            return

        # Call backend to register user (simulate)
        res = backend_api.register_user(stripe_customer_id, name)
        if res.get("status") != "success":
            messagebox.showerror("Error", f"Failed to register user: {res.get('error')}")
            return

        # Save user locally
        new_user = register_user(name, stripe_customer_id, self.face_embedding)
        USERS.append(new_user)
        save_face_image(new_user["user_id"], self.captured_frame)

        messagebox.showinfo("Success", f"✅ Registered {name} successfully.")
        self.reset_register_form()

    def reset_register_form(self):
        self.reg_stripe_id.delete(0, tk.END)
        self.reg_name.delete(0, tk.END)
        self.face_embedding = None
        self.captured_frame = None
        self.register_status.config(text="")
        self.register_button.config(state=tk.DISABLED)

    # --------- PAYMENT TAB -----------
    def build_payment_tab(self):
        tk.Label(self.payment_tab, text="Recipient Stripe Connect Account ID").pack(pady=5)
        self.recipient_entry = tk.Entry(self.payment_tab)
        self.recipient_entry.pack()

        tk.Label(self.payment_tab, text="Amount (GBP)").pack(pady=5)
        self.amount_entry = tk.Entry(self.payment_tab)
        self.amount_entry.pack()

        self.pay_video_label = tk.Label(self.payment_tab)
        self.pay_video_label.pack(pady=10)

        self.verify_button = tk.Button(self.payment_tab, text="🔐 Verify Face", command=self.verify_face_for_payment)
        self.verify_button.pack(pady=5)

        self.payment_status = tk.Label(self.payment_tab, text="", fg="blue")
        self.payment_status.pack()

        self.send_button = tk.Button(self.payment_tab, text="💸 Send Payment", command=self.send_payment, state=tk.DISABLED)
        self.send_button.pack(pady=10)

    def verify_face_for_payment(self):
        ret, frame = CAP.read()
        if not ret:
            messagebox.showerror("Error", "Could not capture frame.")
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            embedding = get_face_embedding(frame_rgb)
            matched_user = match_face(embedding, USERS)
            if matched_user:
                self.face_verified = True
                self.sender_id = matched_user["user_id"]
                self.payment_status.config(text=f"✅ Verified: {matched_user['name']}", fg="green")
                self.send_button.config(state=tk.NORMAL)
            else:
                self.payment_status.config(text="❌ Face not recognized", fg="red")
                self.face_verified = False
                self.send_button.config(state=tk.DISABLED)
        except Exception as e:
            print("Verification error:", e)
            self.payment_status.config(text="❌ Verification failed", fg="red")

    def send_payment(self):
        if not self.face_verified:
            messagebox.showerror("Error", "Verify your face first.")
            return

        recipient_account_id = self.recipient_entry.get().strip()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid amount.")
            return

        if amount <= 0:
            messagebox.showerror("Error", "Amount must be greater than zero.")
            return

        # Validate recipient
        res = backend_api.validate_recipient(recipient_account_id)
        if res.get("status") != "success" or not res.get("valid"):
            messagebox.showerror("Error", "Invalid recipient Stripe Connect Account ID.")
            return

        amount_cents = int(amount * 100)

        # Send transfer via backend
        result = backend_api.send_transfer(
            sender_customer_id=self.sender_id,
            recipient_account_id=recipient_account_id,
            amount_cents=amount_cents
        )

        if result.get("status") == "success":
            messagebox.showinfo("Success", f"Payment sent! Charge ID: {result.get('charge_id')}")
        else:
            messagebox.showerror("Payment Failed", result.get("error") or "Unknown error.")

    def update_video_feed(self):
        ret, frame = CAP.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            if self.register_tab.winfo_ismapped():
                self.reg_video_label.imgtk = imgtk
                self.reg_video_label.configure(image=imgtk)
            if self.payment_tab.winfo_ismapped():
                self.pay_video_label.imgtk = imgtk
                self.pay_video_label.configure(image=imgtk)
        self.root.after(30, self.update_video_feed)

if __name__ == "__main__":
    root = tk.Tk()
    app = FacePayApp(root)
    root.mainloop()

CAP.release()


# All should be under one account-platform. There you create connect account under connect,
#and customers (nearby connect, on the left slide bar, after "home, balances, transactions")
