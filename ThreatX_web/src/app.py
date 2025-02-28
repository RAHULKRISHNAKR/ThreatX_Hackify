from flask import Flask, render_template, request, jsonify
from hackbot.hackbot import Print_AI_out, AI_OPTION
import traceback
from functools import lru_cache

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

@app.route('/')
def home():
    return render_template('index.html')  # Make sure index.html exists in templates folder

@app.route('/chatbot')
def chatbot():
    return render_template('cybercrime_chatbot.html')  # Make sure this file exists in templates folder

# Cache frequent responses
@lru_cache(maxsize=100)
def get_cached_response(prompt):
    return Print_AI_out(prompt, AI_OPTION)

@app.route('/api/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'response': 'No message provided'}), 400
        
    try:
        # Try to get cached response first
        response = get_cached_response(user_input)
        
        # Simple cleanup
        clean_text = str(response).strip()
        clean_text = ' '.join(clean_text.split())
        
        return jsonify({'response': clean_text})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'response': 'An error occurred while processing your request.'}), 500

if __name__ == "__main__":
    app.run(debug=True)