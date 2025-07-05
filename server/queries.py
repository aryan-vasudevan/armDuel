# setup stuff

from pymongo import MongoClient
from dotenv_vault import load_dotenv
import os

load_dotenv(dotenv_path="./.env")
MONGODB_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGODB_URI)

db = client["website"]
questions = db["questions"]
users = db["users"]

# query stuff
question_batch = [
  {
    "question": "What kind of attack involves overwhelming a server with traffic?",
    "wrongAnswers": ["Phishing", "Brute force", "Man-in-the-middle"],
    "correctAnswer": "DDoS attack",
    "category": "cybersecurity"
  },
  {
    "question": "Which of the following is an example of a phishing attack?",
    "wrongAnswers": ["Installing software updates", "Using a VPN", "Encrypting a hard drive"],
    "correctAnswer": "Sending a fake login page to steal credentials",
    "category": "cybersecurity"
  },
  {
    "question": "What does a firewall do?",
    "wrongAnswers": ["Stores passwords", "Detects viruses", "Encrypts messages"],
    "correctAnswer": "Blocks unauthorized access to a network",
    "category": "cybersecurity"
  },
  {
    "question": "What is the best way to protect your accounts online?",
    "wrongAnswers": ["Use the same password everywhere", "Click on all email links", "Turn off antivirus"],
    "correctAnswer": "Use unique, strong passwords for each account",
    "category": "cybersecurity"
  },
  {
    "question": "What is a common indicator of a phishing email?",
    "wrongAnswers": ["Personalized greeting", "Correct grammar", "Sent from a known contact"],
    "correctAnswer": "Urgent request for login or payment with suspicious link",
    "category": "cybersecurity"
  },
  {
    "question": "Which device is most vulnerable to security threats when not updated?",
    "wrongAnswers": ["TV remote", "Power strip", "Light bulb"],
    "correctAnswer": "Smartphone",
    "category": "cybersecurity"
  },
  {
    "question": "What kind of attack captures data between two parties without them knowing?",
    "wrongAnswers": ["SQL injection", "Ransomware", "Phishing"],
    "correctAnswer": "Man-in-the-middle attack",
    "category": "cybersecurity"
  },
  {
    "question": "Which of these is the safest way to store your passwords?",
    "wrongAnswers": ["Write them on paper", "Reuse the same password", "Save in a text file"],
    "correctAnswer": "Use a trusted password manager",
    "category": "cybersecurity"
  },
  {
    "question": "What is the main goal of social engineering attacks?",
    "wrongAnswers": ["Fix bugs", "Speed up internet", "Encrypt data for backup"],
    "correctAnswer": "Trick people into revealing sensitive information",
    "category": "cybersecurity"
  },
  {
    "question": "What should you do if you receive an unexpected email with an attachment?",
    "wrongAnswers": ["Open it immediately", "Forward it to friends", "Reply asking for more info"],
    "correctAnswer": "Delete it or verify with the sender first",
    "category": "cybersecurity"
  }
]



questions.insert_many(question_batch)