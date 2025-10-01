import tkinter as tk
from tkinter import filedialog, scrolledtext
import os
from uuid import uuid4
from markdown import markdown
import asyncio

from agent import send_clarification, send_message

class AgentUI:
    def __init__(self, root, loop):
        self.root = root
        self.root.title("Codebase Research Agent")
        self.isFirstMsg = True
        self.loop = loop

        # --- Repo selection ---
        self.repo_frame = tk.Frame(root)
        self.repo_frame.pack(padx=10, pady=10, fill="x")
        tk.Label(self.repo_frame, text="Repository Path:").pack(side="left")
        self.repo_entry = tk.Entry(self.repo_frame, width=50)
        self.repo_entry.pack(side="left", padx=5)
        tk.Button(self.repo_frame, text="Browse", command=self.browse_repo).pack(side="left")
        tk.Button(self.repo_frame, text="Set Path", command=self.set_repo_path).pack(side="left")

        # --- Conversation display ---
        self.chat_display = scrolledtext.ScrolledText(root, height=20, width=80, state="disabled")
        self.chat_display.pack(padx=10, pady=10)

        # --- User input ---
        self.input_frame = tk.Frame(root)
        self.input_frame.pack(padx=10, pady=5, fill="x")
        self.user_entry = tk.Entry(self.input_frame, width=60)
        self.user_entry.pack(side="left", padx=5)
        self.user_entry.bind("<Return>", self.submit_input)
        self.submit_button = tk.Button(self.input_frame, text="Submit", command=self.submit_input)
        self.submit_button.pack(side="left")

        # State variables
        self.agent_state = None
        self.thread_config = {"configurable": {"thread_id": str(uuid4())}}

    def browse_repo(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_entry.delete(0, tk.END)
            self.repo_entry.insert(0, path)

    def set_repo_path(self):
        path = self.repo_entry.get().strip()
        if not os.path.exists(path) or not os.path.isdir(path):
            self.display_message("System", "Invalid directory path!")
            return
        self.display_message("System", f"Repository path set to: {path}")
        self.repo_entry.config(state="disabled")

    def get_repo_path(self):
        return self.repo_entry.get()

    def display_message(self, sender, message):
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def submit_input(self, event=None):
        print("hi")
        user_text = self.user_entry.get().strip()

        if not user_text:
            return
        
        self.user_entry.delete(0, tk.END)
        self.display_message("You", user_text)
        
        # Check if file path exists
        repo_path = self.get_repo_path()
        if not repo_path or not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            self.display_message("System", "Please choose a valid repository path before asking questions.")
            return

        # Show loading text
        self.loading_label = tk.Label(self.root, text="Agent is thinking...", fg="red")
        self.loading_label.pack(pady=5)

        if self.isFirstMsg:
            self.isFirstMsg = False
            loop.create_task(self.handle_agent(user_text, "msg"))
        else:
            loop.create_task(self.handle_agent(user_text, "clr"))

    async def handle_agent(self, user_text, category):
        try:
            if category == "msg":
                response = await send_message(user_text, self.repo_entry.get())
            else:
                response = await send_clarification(user_text, self.repo_entry.get())
        finally:
            if hasattr(self, "loading_label") and self.loading_label.winfo_exists():
                self.loading_label.destroy()

        self.display_message("Agent", response)

    #def run(self):
    #    self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    loop = asyncio.get_event_loop()
    app = AgentUI(root, loop)

    def async_loop():
        try:
            root.update()
        except tk.TclError:
            return
        loop.call_later(0.01, async_loop)
    
    loop.call_soon(async_loop)
    loop.run_forever()
