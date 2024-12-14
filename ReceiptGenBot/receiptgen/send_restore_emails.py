import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(smtp_server, port, username, password, to_email, subject, body, html_body):
    # Create a multipart email message
    msg = MIMEMultipart()
    msg['From'] = f"AmethyX Generator <{username}>"  # Set sender name and email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        # Establish a secure session with the server
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Upgrade to a secure connection
            server.login(username, password)  # Log in to the server
            server.send_message(msg)  # Send the email
        print(f"Email sent successfully! {to_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")


def send_emails_from_file(file_path, smtp_server, port, username, password, subject, body, email_body):
    """Read email addresses from a file and send emails to each address."""
    try:
        with open(file_path, 'r') as file:
            emails = file.readlines()

        # Send an email to each address found in the file
        for email in emails:
            email = email.strip()  # Remove any extra whitespace or newline characters
            if email:  # Ensure the email is not an empty string
                send_email(smtp_server, port, username, password, email, subject, body, email_body)
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

email_html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Receipt Generator is Back!</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');


      body {
        margin: 0;
        padding: 0;
        font-family: 'Poppins', sans-serif;
        background-color: #f4f4f4;
      }

      .container {
        max-width: 600px;
        margin: 0 auto;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      }

      .banner {
        border-bottom: 5px solid #9966cc;
        background: #323232;

      }

      .banner img {
        width: 100%;
        height: auto;
        display: block;
      }

      .content {
        padding: 20px;
        text-align: center;
        color: #333333;
      }

      .content p {
        font-size: 16px;
        line-height: 1.5;
        margin: 0 0 20px;
        color: #555;
      }

      .content h1 {
        font-size: 25px;
        color: #9966cc;
        font-weight: bold;
        margin-bottom: 15px;
      }

      .button {
        display: inline-block;
        padding: 15px 30px;
        background-color: #9966cc;
        color: white;
        text-decoration: none;
        border-radius: 5px;
        font-weight: 600;
        font-size: 16px;
      }

      .button:hover {
        background-color: #8551b1;
      }

      .footer {
        padding: 20px;
        text-align: center;
        background-color: #f4f4f4;
        font-size: 12px;
        color: #999999;
      }
      .footer p {
        margin: 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="banner">
        <img src="https://i.postimg.cc/T3v0JBdy/amethyx-banner-clear.png" alt="Banner" style="display: block; width: 100%; max-width: 600px; height: auto;">
      </div>
      <div class="content">
        <h1>Receipt Generator!</h1>
        <p>We’re sorry that the public bot in <span style="font-weight: bold;">ResellVendorHub</span> got disabled<br> To continue using this service and many more like <span style="font-weight: bold;">Paper Receipts</span> and <span style="font-weight: bold;">Fake StockX App</span>, we invite you to join the official AmethyX discord server</p>
        <a href="https://discord.gg/amethyx1" class="button">Get Receipts Here</a>
      </div>
      <div class="footer">
        <p>©2024 Amethyx.net</p>
        <p>contact@amethyx.net</p>
      </div>
    </div>
  </body>
</html>
"""


# Example usage:
if __name__ == "__main__":
    smtp_server = 'mail.amethyx.cc'  # Use Gmail's SMTP server
    port = 587
    username = 'amethyx'  # Your email address
    password = '7802E4rjpXEM'  # Your email account password
    subject = 'Get Receipt Generator Back Here'
    body = 'Hello user'

    send_emails_from_file("emails.txt", smtp_server, port, username, password, subject, body, email_html)
