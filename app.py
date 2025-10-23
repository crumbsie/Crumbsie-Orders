import imaplib
import email
from email.header import decode_header
import streamlit as st

EMAIL_USER = "crumbsiebakes@gmail.com"
EMAIL_PASS = "neyg ellj qwuy giys"
IMAP_SERVER = "imap.gmail.com"

if "orders" not in st.session_state:
    st.session_state.orders = []
if "processed_email_ids" not in st.session_state:
    st.session_state.processed_email_ids = set()

def parse_order_from_body(body):
    order_info = {}
    lines = [line.replace('\xa0',' ').strip() for line in body.splitlines() if ':' in line]
    for line in lines:
        key, value = line.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        if "first name" in key: order_info["first_name"] = value
        elif "last name" in key: order_info["last_name"] = value
        elif key == "email": order_info["email"] = value
        elif "address" in key: order_info["address"] = value
        elif "cake type" in key: order_info["cake_type"] = value
        elif "customization" in key: order_info["customization"] = value
        elif "cake needed" in key: order_info["cake_needed_by"] = value
    order_info["completed"] = False
    return order_info if "first_name" in order_info else None

def fetch_orders():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        status, messages = mail.search(None, '(SUBJECT "Place cake order got a new submission")')
        email_ids = messages[0].split()
        for e_id in email_ids:
            if e_id in st.session_state.processed_email_ids:
                continue
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    if subject == "Place cake order got a new submission":
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    raw_payload = part.get_payload(decode=True)
                                    try: body = raw_payload.decode('utf-8')
                                    except: body = raw_payload.decode('utf-8', errors='ignore')
                        else:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        order_info = parse_order_from_body(body)
                        if order_info:
                            existing_numbers = [o["order_number"] for o in st.session_state.orders]
                            next_number = max(existing_numbers)+1 if existing_numbers else 1
                            order_info["order_number"] = next_number
                            st.session_state.orders.append(order_info)
            mail.store(e_id, '+FLAGS', '\\Seen')
            st.session_state.processed_email_ids.add(e_id)
        mail.logout()
    except Exception as e:
        st.error(f"Error fetching emails: {e}")

st.title("Crumbsie Orders")

tab1, tab2 = st.tabs(["New Orders", "Completed Orders"])

fetch_orders()  # fetch emails every time page loads

def display_orders(filter_completed):
    for order in st.session_state.orders:
        if order["completed"] != filter_completed:
            continue
        with st.expander(f"Order #{order['order_number']} - {order['first_name']} {order['last_name']}"):
            st.write(f"Email: {order['email']}")
            st.write(f"Address: {order['address']}")
            st.write(f"Cake Type: {order['cake_type']}")
            st.write(f"Customization: {order['customization']}")
            st.write(f"Needed By: {order['cake_needed_by']}")
            if st.button("Complete" if not order["completed"] else "Archive", key=order['order_number']):
                order["completed"] = not order["completed"]
                st.experimental_rerun()

with tab1:
    display_orders(False)
with tab2:
    display_orders(True)
