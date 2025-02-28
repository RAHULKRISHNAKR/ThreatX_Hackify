from flask import Flask, render_template, request, jsonify
from hackbot.hackbot import Print_AI_out, AI_OPTION

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    response = Print_AI_out(user_input, AI_OPTION)
    return jsonify({'response': response})

if __name__ == "__main__":
    app.run(debug=True)