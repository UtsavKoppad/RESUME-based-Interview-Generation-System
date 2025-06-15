 #app.py 
import os
import speech_recognition as sr
import PyPDF2
import cohere
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for session handling

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

COHERE_API_KEY = "" # Replace with your API key
co = cohere.Client(COHERE_API_KEY)

# Extract text from PDF resume
def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            return " ".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
    except:
        return None

# Generate structured interview questions
def generate_interview_questions(resume_text):
    prompt = f"Generate exactly 5 technical interview questions based on this resume:\n{resume_text}\nProvide them as a numbered list."
    response = co.generate(model="command", prompt=prompt, max_tokens=300)

    raw_questions = response.generations[0].text.split("\n")
    
    # Extract clean questions
    questions = []
    for q in raw_questions:
        clean_q = q.strip()
        if clean_q and any(char.isalpha() for char in clean_q):  # Ensures it's a valid question
            clean_q = clean_q.split(".", 1)[-1].strip()  # Remove numbering
            questions.append(clean_q)

    return questions[:5]  # Ensuring only 5 questions are returned

# Evaluate the answer
def evaluate_answer(answer):
    prompt = f"Evaluate this answer in an interview and provide a score out of 10 with brief feedback:\nAnswer: {answer}"
    response = co.generate(model="command", prompt=prompt, max_tokens=50)
    return response.generations[0].text

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    resume_text = extract_text_from_pdf(file_path)
    if not resume_text:
        return jsonify({"error": "Could not extract text from resume"}), 400

    questions = generate_interview_questions(resume_text)
    if not questions:
        return jsonify({"error": "No questions generated. Please try again."}), 400

    session["questions"] = questions  # Store in session for the next page
    return redirect(url_for("show_questions"))

@app.route("/show_questions")
def show_questions():
    questions = session.get("questions", [])  # Ensure it exists
    return render_template("questions.html", questions=questions)


@app.route("/evaluate_answer", methods=["POST"])
def evaluate():
    data = request.json
    answer = data.get("answer", "").strip()
    if not answer:
        return jsonify({"error": "No answer provided"}), 400

    evaluation = evaluate_answer(answer)
    return jsonify({"evaluation": evaluation})

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            return jsonify({"transcription": text})
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand speech"}), 400
        except sr.RequestError:
            return jsonify({"error": "Speech recognition service error"}), 500

if __name__ == "__main__":
    app.run(debug=True)


