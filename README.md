# FileOrganizer Pro
🗂️ File Organizer Pro

A desktop-based file management application built using Python and PyQt5, designed to organize files efficiently with a clean, modern interface. 
The tool supports smart file sorting, previewing, drag-and-drop organization, and secure file encryption, making file handling fast, structured, and user-friendly.
A modern PyQt5-based file organizer that lets you view files as tiles, filter by type, preview files, and organize them by type or date. It also supports encryption/decryption of files and folders using AES-256.

🧩 Tech Stack

Language: Python
Framework: PyQt5
Security: AES-256 Encryption (Cryptography library)
Packaging: PyInstaller

🚀 Features

✔️ Modern and responsive PyQt5 UI
✔️ Sort files by type, date, or name
✔️ Real-time file filtering and search
✔️ File preview support
✔️ Drag-and-drop functionality
✔️ AES-256 encryption & decryption for secure files
✔️ Move files automatically into categorized folders
✔️ Option to generate compiled .exe for distribution

Installation

Clone the repository:
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

⚠️ Python 3.8+ recommended.

Install required dependencies:
pip install -r requirements.txt

🔐 Encryption Feature

Files can be encrypted and decrypted using AES-256, ensuring data protection and secure storage for sensitive information.

🖥️ Build Windows Executable (.exe)

To generate a standalone Windows executable using PyInstaller:
pyinstaller -F -w -i icon.ico file_organizer.py

📌 Meaning of the flags:

Flag	Description
-F	Builds a single executable file
-w	Runs without opening console window
-i icon.ico	Optional – sets custom icon

After building, the .exe will be located in:
dist/


