from flask import Flask, render_template, request, jsonify
from hackbot.hackbot import Print_AI_out, AI_OPTION, initialize_gemini
import traceback
from functools import lru_cache

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

if AI_OPTION == "GEMINI":
    initialize_gemini()

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
    try:
        user_input = request.json.get('message', '')
        if not user_input:
            return jsonify({'response': 'No message provided'}), 400

        print(f"Processing request: {user_input[:100]}...")
        
        response = get_cached_response(user_input)
        
        if "Rate limit exceeded" in response:
            return jsonify({'response': response}), 429
        elif "Error:" in response:
            print(f"API error response: {response}")
            return jsonify({'response': response}), 200
            
        return jsonify({'response': response})

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'response': 'The service is temporarily unavailable. Please try again later.'
        }), 500
    
if __name__ == "__main__":
    app.run(debug=True)