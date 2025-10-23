import imaplib
import email
from email.header import decode_header
import tkinter as tk
from tkinter import ttk

# ---------------- Gmail Credentials ----------------
EMAIL_USER = "crumbsiebakes@gmail.com"
EMAIL_PASS = "neyg ellj qwuy giys"  # <-- Replace with your app password
IMAP_SERVER = "imap.gmail.com"

orders = []  # start empty
processed_email_ids = set()  # keeps track of Gmail IDs we've already added

# ---------------- GUI Setup ----------------
root = tk.Tk()
root.title("Crumbsie Orders")
root.geometry("900x600")

# Header
header_frame = tk.Frame(root)
header_frame.pack(fill="x", padx=10, pady=10)
header_label = tk.Label(header_frame, text="Crumbsie Orders", font=("Arial", 24, "bold"))
header_label.pack(side="left")

# Tabs
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)
new_orders_frame = tk.Frame(notebook)
completed_orders_frame = tk.Frame(notebook)
notebook.add(new_orders_frame, text="New Orders")
notebook.add(completed_orders_frame, text="Completed Orders")

# Scrollable frame utility
def create_scrollable_frame(parent):
    canvas = tk.Canvas(parent)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas)
    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return scroll_frame

new_orders_scroll = create_scrollable_frame(new_orders_frame)
completed_orders_scroll = create_scrollable_frame(completed_orders_frame)

# ---------------- Email Parsing ----------------
def parse_order_from_body(body):
    order_info = {}
    lines = [line.replace('\xa0', ' ').strip() for line in body.splitlines() if ':' in line]
    for line in lines:
        key, value = line.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        if "first name" in key:
            order_info["first_name"] = value
        elif "last name" in key:
            order_info["last_name"] = value
        elif key == "email":
            order_info["email"] = value
        elif "address" in key:
            order_info["address"] = value
        elif "cake type" in key:
            order_info["cake_type"] = value
        elif "customization" in key:
            order_info["customization"] = value
        elif "cake needed" in key:
            order_info["cake_needed_by"] = value
    order_info["completed"] = False
    return order_info if "first_name" in order_info else None

# ---------------- Collapsible Order Display ----------------
order_frames = {}  # order_number -> frame

def toggle_order_details(details_frame):
    if details_frame.winfo_viewable():
        details_frame.pack_forget()
    else:
        details_frame.pack(fill="x", pady=2)

def refresh_orders():
    for widget in new_orders_scroll.winfo_children():
        widget.destroy()
    for widget in completed_orders_scroll.winfo_children():
        widget.destroy()

    for order in sorted(orders, key=lambda x: x["order_number"]):
        parent_frame = tk.Frame(
            new_orders_scroll if not order["completed"] else completed_orders_scroll,
            bd=1, relief="solid", padx=5, pady=5
        )
        parent_frame.pack(fill="x", padx=5, pady=5)

        # Header: only Order # and Name
        header_frame = tk.Frame(parent_frame)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text=f"Order #{order['order_number']}", width=10, anchor="w").pack(side="left")
        tk.Label(header_frame, text=f"{order['first_name']} {order['last_name']}", width=25, anchor="w").pack(side="left")

        # Button to expand/collapse
        details_frame = tk.Frame(parent_frame)
        details_frame.pack_forget()  # start collapsed

        def make_toggle(frame=details_frame):
            return lambda e=None: toggle_order_details(frame)
        header_frame.bind("<Button-1>", make_toggle())
        for child in header_frame.winfo_children():
            child.bind("<Button-1>", make_toggle())

        # Details: Customer + Cake info
        top_row = tk.Frame(details_frame)
        top_row.pack(fill="x", pady=2)
        tk.Label(top_row, text=f"Email: {order['email']}", width=30, anchor="w").pack(side="left")
        tk.Label(top_row, text=f"Address: {order['address']}", width=40, anchor="w").pack(side="left")

        bottom_row = tk.Frame(details_frame)
        bottom_row.pack(fill="x", pady=2)
        tk.Label(bottom_row, text=f"Cake Type: {order['cake_type']}", anchor="w").pack(fill="x")
        tk.Label(bottom_row, text=f"Customization: {order['customization']}", anchor="w").pack(fill="x")
        tk.Label(bottom_row, text=f"Needed By: {order['cake_needed_by']}", anchor="w").pack(fill="x")

        # Right: checkbox + button
        action_frame = tk.Frame(details_frame)
        action_frame.pack(side="right", padx=5)
        var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(action_frame, variable=var)
        cb.pack(side="top")

        def make_action(order=order):
            def action():
                order["completed"] = not order["completed"]
                refresh_orders()
            return action

        btn = tk.Button(action_frame, text="Complete" if not order["completed"] else "Archive", command=make_action())
        btn.pack(side="top")

        order_frames[order["order_number"]] = parent_frame

# ---------------- Fetch Emails ----------------
def fetch_orders():
    global orders
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, '(SUBJECT "Place cake order got a new submission")')
        email_ids = messages[0].split()

        for e_id in email_ids:
            if e_id in processed_email_ids:
                continue  # skip emails we've already added

            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    if subject == "Place cake order got a new submission":
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    raw_payload = part.get_payload(decode=True)
                                    try:
                                        body = raw_payload.decode('utf-8')
                                    except UnicodeDecodeError:
                                        try:
                                            body = raw_payload.decode('latin1')
                                        except:
                                            body = raw_payload.decode('utf-8', errors='ignore')
                        else:
                            raw_payload = msg.get_payload(decode=True)
                            try:
                                body = raw_payload.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    body = raw_payload.decode('latin1')
                                except:
                                    body = raw_payload.decode('utf-8', errors='ignore')

                        order_info = parse_order_from_body(body)
                        if order_info:
                            existing_numbers = [o["order_number"] for o in orders]
                            next_number = max(existing_numbers)+1 if existing_numbers else 1
                            order_info["order_number"] = next_number
                            orders.append(order_info)

            # Mark email as read and processed
            mail.store(e_id, '+FLAGS', '\\Seen')
            processed_email_ids.add(e_id)

        mail.logout()
        refresh_orders()
    except Exception as e:
        print("Error fetching emails:", e)

    # Schedule next fetch in 60 seconds
    root.after(60000, fetch_orders)

# Start fetching
fetch_orders()
root.mainloop()
