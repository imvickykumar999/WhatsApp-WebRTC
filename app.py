from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

logging.getLogger('watchdog').setLevel(logging.CRITICAL)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/get_incoming_call', methods=['GET'])
def get_incoming_call():
    api_url = "https://chat.bol7.com/api/chat/incomingcalls"
    headers = {
        'Authorization': 'Bearer 5hAaoWo6jaoL0Vp6kr6BqPtJplf2Q9WHtpUWOS%252Bp1d3GJ3R6PVbKsZur%252B5oYokiHaisZ7lpwOBJkofEoiYdpmMp%252F8GoPSNX%252BUGss2UeQ%252FK0VNi608uhVplnvvonzBgYm%252F933sNL%252BR0jmkvUqpfrANA%253D%253D'
    }
    try:
        logging.debug(f"Making request to {api_url} with headers {headers}")
        response = requests.get(api_url, headers=headers)
        logging.debug(f"Response: {response.status_code} {response.text}")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch data", "status_code": response.status_code}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/answer_call', methods=['POST'])
def answer_call():
    try:
        # Extract incoming call details from the request body
        incoming_data = request.json
        logging.debug(f"Incoming data: {incoming_data}")

        # Get the SDP string directly from the incoming data
        sdp_offer = incoming_data.get("sdp")
        
        if not sdp_offer:
            logging.error("SDP is missing from the request data")
            return jsonify({"error": "SDP is required"}), 400

        # Call the function to create the minimal SDP answer
        sdp_answer = _create_minimal_sdp_answer(sdp_offer)
        
        # Prepare the data to send to the external API
        data = {
            "id": incoming_data["id"],  # The ID from the incoming call details
            "sessioncalls": {
                "sdp": sdp_answer,  # Use the generated minimal SDP answer
                "sdp_type": "answer"  # Set the sdp_type to "answer"
            }
        }

        logging.debug(f"Prepared data to answer the call: {data}")

        # Make the POST request to answer the call
        post_url = "https://chat.bol7.com/api/chat/answercall"
        headers = {
            'Authorization': 'Bearer 5hAaoWo6jaoL0Vp6kr6BqPtJplf2Q9WHtpUWOS%252Bp1d3GJ3R6PVbKsZur%252B5oYokiHaisZ7lpwOBJkofEoiYdpmMp%252F8GoPSNX%252BUGss2UeQ%252FK0VNi608uhVplnvvonzBgYm%252F933sNL%252BR0jmkvUqpfrANA%253D%253D'
        }

        # Send the request to the external API
        response = requests.post(post_url, json=data, headers=headers)

        # Log the response for debugging purposes
        logging.debug(f"Response from answer call API: {response.status_code} {response.text}")

        # Check the response from the external API
        if response.status_code == 200 and response.json().get("success"):
            return jsonify({"message": "Call answered successfully", "response": response.json()})
        else:
            error_message = response.json().get("message", "Unknown error")
            logging.error(f"Error in answering the call: {error_message}")
            return jsonify({"error": error_message, "response": response.json()}), 500

    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception: {str(e)}")
        return jsonify({"error": f"Request exception: {str(e)}"}), 500

    except Exception as e:
        logging.error(f"General exception: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/api/reject_call', methods=['POST'])
def reject_call():
    try:
        call_id = request.json.get('id')  # Get the call ID from the request body
        if not call_id:
            return jsonify({"error": "Call ID is required"}), 400

        api_url = f"https://chat.bol7.com/api/chat/rejectcall?id={call_id}"
        headers = {
            'Authorization': 'Bearer 5hAaoWo6jaoL0Vp6kr6BqPtJplf2Q9WHtpUWOS%252Bp1d3GJ3R6PVbKsZur%252B5oYokiHaisZ7lpwOBJkofEoiYdpmMp%252F8GoPSNX%252BUGss2UeQ%252FK0VNi608uhVplnvvonzBgYm%252F933sNL%252BR0jmkvUqpfrANA%253D%253D'
        }

        # Send the reject call request
        response = requests.post(api_url, headers=headers)

        # Log the response for debugging purposes
        logging.debug(f"Response from reject call API: {response.status_code} {response.text}")

        if response.status_code == 200:
            return jsonify({"message": "Call rejected successfully", "response": response.json()})
        else:
            error_message = response.json().get("message", "Unknown error")
            logging.error(f"Error in rejecting the call: {error_message}")
            return jsonify({"error": error_message, "response": response.json()}), 500

    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception: {str(e)}")
        return jsonify({"error": f"Request exception: {str(e)}"}), 500

    except Exception as e:
        logging.error(f"General exception: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def _create_minimal_sdp_answer(offer_sdp: str) -> str:
    """Create minimal SDP answer that exactly matches expected format"""
    
    # Parse offer to extract required values
    offer_lines = offer_sdp.strip().split('\r\n')
    
    ice_ufrag = None
    ice_pwd = None
    fingerprint = None
    msid = None
    
    for line in offer_lines:
        if line.startswith('a=ice-ufrag:'):
            ice_ufrag = line.split(':')[1]
        elif line.startswith('a=ice-pwd:'):  
            ice_pwd = line.split(':')[1]
        elif line.startswith('a=fingerprint:'):
            fingerprint = line.split(':', 1)[1]
        elif line.startswith('a=msid:'):
            msid = line.split(':', 1)[1].split()[0]
    
    print(f"Extracted ICE ufrag: {ice_ufrag}")
    print(f"Extracted ICE pwd: {ice_pwd}")
    print(f"Extracted fingerprint: {fingerprint[:20]}...")
    print(f"Extracted MSID: {msid}")
    
    # Generate answer SDP that mirrors offer structure
    answer_sdp = f"""v=0\r
o=- 3965362799 3965362799 IN IP4 0.0.0.0\r
s=-\r
t=0 0\r
a=group:BUNDLE audio\r
a=msid-semantic: WMS {msid or 'aiortc-stream'}\r
m=audio 9 UDP/TLS/RTP/SAVPF 111 126\r
c=IN IP4 0.0.0.0\r
a=rtcp:9 IN IP4 0.0.0.0\r
a=ice-ufrag:{ice_ufrag}\r
a=ice-pwd:{ice_pwd}\r
a=fingerprint:{fingerprint}\r
a=setup:active\r
a=mid:audio\r
a=sendrecv\r
a=rtcp-mux\r
a=rtpmap:111 opus/48000/2\r
a=rtcp-fb:111 transport-cc\r
a=fmtp:111 maxaveragebitrate=20000;maxplaybackrate=16000;minptime=20;sprop-maxcapturerate=16000;useinbandfec=1\r
a=rtpmap:126 telephone-event/8000\r
a=maxptime:20\r
a=ptime:20\r
a=ssrc:2195401356 cname:AiortcAudioStream1\r
"""
    
    print(f"Generated minimal SDP answer ({len(answer_sdp)} characters)")
    return answer_sdp


if __name__ == '__main__':
    app.run(debug=True)
