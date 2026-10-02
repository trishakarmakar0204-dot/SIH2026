# MEMBER 5: Raspberry Pi kiosk
1. Install Raspberry Pi OS, then: sudo apt install fonts-noto chromium-browser
2. Run the backend on a laptop on the same Wi-Fi (or hotspot): uvicorn backend.main:app --host 0.0.0.0
3. On the Pi, open the laptop's address in kiosk mode:
   chromium-browser --kiosk --unsafely-treat-insecure-origin-as-secure=http://LAPTOP_IP:8000 --user-data-dir=/tmp/k http://LAPTOP_IP:8000
   (the flag lets the browser use the microphone over plain http)
4. Plug in USB mic + speaker, set them as defaults, test with a spoken question.
