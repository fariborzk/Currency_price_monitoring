# رفتن به مسیر پروژه
Set-Location "C:\Users\harikof\Desktop\SendCurrencyPrices"

# فعال کردن محیط مجازی
& .\.venv\Scripts\Activate.ps1

# اجرای کد با شماره موبایل
python tgn_monitor.py login --phone 09134351050
