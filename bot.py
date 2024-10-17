from flask import Flask, render_template, request
import telebot



app = Flask(__name__)

bot = telebot.TeleBot("6359406356:AAGGrTux4ZAi20ivcIffoiNOrnMOvf3dyBc")

@app.route('/bot_webhook', methods=['POST'])
def bot_webhook():
  bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
  return 'OK'


@app.route('/set_app', methods=['GET'])
def set_app():
  bot.remove_webhook()
  bot.set_webhook("https://" + request.host + "/bot_webhook")
  return 'Done'


def GET(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
        'Accept': 'application/json, text/javascript',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    return requests.get(url, headers=headers)

# Function to perform a GET request with custom headers including cookies
def GET_h(url, ttwid, passport_csrf_token):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
        'Accept': 'application/json, text/javascript',
        'Content-Type': 'application/x-www-form-urlencoded',
        'cookie': f'ttwid={ttwid}; passport_csrf_token={passport_csrf_token};',
        'x-tt-passport-csrf-token': f'{passport_csrf_token}'
    }
    return requests.get(url, headers=headers)

# Function to decode escape sequences in a URL
def convert_escape_sequence(s):
    return s.encode().decode('unicode_escape')

# Function to shorten a URL using TikTok's URL shortening service
def short_url(url_to_short):
    url = "https://www.tiktok.com/shorten/?aid=1988"
    payload = {
        'targets': url_to_short,
        'belong': 'tiktok-webapp-qrcode'
    }
    response = requests.post(url, data=payload)
    url_shorten_list = re.findall(r'"short_url":"(.*?)"', response.text)
    url_shorten = url_shorten_list[0] if url_shorten_list else None
    return url_shorten

# Function to retrieve the QR code URL and related tokens
def get_qrcode_url():
    url = "https://www.tiktok.com/passport/web/get_qrcode/?next=https://www.tiktok.com&aid=1459"
    response = requests.post(url)
    cookies = response.cookies

    passport_csrf_token = cookies.get('passport_csrf_token')
    ttwid = GET('https://www.tiktok.com/login/qrcode')
    ttwid = ttwid.cookies.get('ttwid')

    token_match = re.search(r'"token":"(.*?)"', response.text)
    qrcode_index_url_match = re.search(r'"qrcode_index_url":"(.*?)"', response.text)

    token = token_match.group(1) if token_match else None
    qrcode_index_url = qrcode_index_url_match.group(1) if qrcode_index_url_match else None
    qrcode_index_url = convert_escape_sequence(qrcode_index_url)

    shorten_url = short_url(qrcode_index_url)
    return token, ttwid, passport_csrf_token, shorten_url

# Function to continuously check for QR code scan and confirmation, and retrieve session ID
def get_session_id(chat_id):
    try:
        token, ttwid, passport_csrf_token, shorten_url = get_qrcode_url()
        bot.send_message(chat_id, f"Please open this URL on your phone to scan the QR code: {shorten_url}")
        
        while True:
            qr_check = GET_h(f'https://web-va.tiktok.com/passport/web/check_qrconnect/?next=https%3A%2F%2Fwww.tiktok.com&token={token}&aid=1459', ttwid, passport_csrf_token)
            if "scanned" in qr_check.text:
                bot.send_message(chat_id, "QR code scanned! Waiting for your confirmation.")
            elif "confirmed" in qr_check.text:
                sessionid = qr_check.cookies.get('sessionid')
                bot.send_message(chat_id, f"Session ID: {sessionid}")
                break
            elif "expired" in qr_check.text:
                token, ttwid, passport_csrf_token, shorten_url = get_qrcode_url()
                bot.send_message(chat_id, f"QR code expired! Please open this new URL: {shorten_url}")
            time.sleep(0.7)

        if sessionid:
            bot.send_message(chat_id, f"Session ID: {sessionid}\nCoded By Hex")
        else:
            bot.send_message(chat_id, "Failed to retrieve Session ID.")
    except Exception as error:
        bot.send_message(chat_id, f"ERROR: {error}")

# Handler for /start command with inline button
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    
    # Create inline button
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Generate QR Code", callback_data="generate_qr")
    markup.add(button)
    
    # Send welcome message with inline button
    bot.send_message(chat_id, "Welcome! Click the button below to generate a QR code.", reply_markup=markup)

# Callback handler for button click
@bot.callback_query_handler(func=lambda call: call.data == "generate_qr")
def handle_callback(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Generating QR code and waiting for confirmation...")
    get_session_id(chat_id)
    bot.infinity_polling() 
if __name__ == '__main__':
    app.run(debug=True)
