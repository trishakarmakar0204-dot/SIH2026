# Raspberry Pi kiosk

1. Install Raspberry Pi OS, then run:

       sudo apt install fonts-noto chromium-browser

2. Run the backend on a laptop on the same Wi-Fi (or hotspot):

       uvicorn backend.main:app --host 0.0.0.0

3. On the Pi, open the laptop's address in kiosk mode (replace `LAPTOP_IP` with the laptop's IP address):

       chromium-browser --kiosk --unsafely-treat-insecure-origin-as-secure=http://LAPTOP_IP:8000 --user-data-dir=/tmp/k http://LAPTOP_IP:8000

   The flag lets the browser use the microphone over plain `http`. Use it only on a network you trust.

4. Plug in a USB microphone and speaker, set them as the defaults, and test with a spoken question.
