import hashlib
import re
from datetime import datetime, date, timedelta
from pathlib import Path

# LibraPay: Automated Library Fine Management
# All records are stored in plain-text .txt files using direct file I/O and | separators.

DATA_DIR = Path(__file__).resolve().parent
STUDENTS_FILE = DATA_DIR / "students.txt"
STAFF_FILE = DATA_DIR / "staff.txt"
BOOKS_FILE = DATA_DIR / "books.txt"
TRANSACTIONS_FILE = DATA_DIR / "transactions.txt"

BORROWING_DAYS = 7
FINE_PER_DAY = 5.00

STUDENT_FIELDS = [
    "student_id", "full_name", "course", "year_level", "section", "password"
]
STAFF_FIELDS = ["username", "full_name", "password"]
BOOK_FIELDS = [
    "book_id", "title", "author", "category", "total_copies", "available_copies"
]
TRANSACTION_FIELDS = [
    "transaction_id", "student_id", "book_id", "request_date", "borrow_date",
    "due_date", "return_date", "status", "fine_paid"
]


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def read_records(path, fields):
    """Read pipe-delimited plain-text records without using CSV."""
    if not path.exists():
        return []

    records = []
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if not lines:
            return []

        # The first line contains field names separated by |.
        stored_fields = [part.strip() for part in lines[0].rstrip("\n").split("|")]

        for line_text in lines[1:]:
            line_text = line_text.rstrip("\r\n")
            if not line_text.strip():
                continue

            values = line_text.split("|")
            record = {}
            for index, field in enumerate(stored_fields):
                record[field] = values[index].strip() if index < len(values) else ""

            # Return only the fields expected by the current program.
            cleaned = {field: record.get(field, "") for field in fields}
            if any(cleaned.values()):
                records.append(cleaned)

    except OSError as error:
        print(f"Could not read {path.name}: {error}")

    return records


def write_records(path, fields, records):
    """Write pipe-delimited plain-text records without using CSV."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write("|".join(fields) + "\n")
            for record in records:
                values = []
                for field in fields:
                    value = str(record.get(field, "") or "")
                    # Prevent delimiters/newlines from breaking the text-file format.
                    value = value.replace("|", "/").replace("\n", " ").replace("\r", " ")
                    values.append(value)
                file.write("|".join(values) + "\n")
        return True
    except OSError as error:
        print(f"Could not save {path.name}: {error}")
        return False


def ensure_data_files():
    """Create data files and seed sample books / default staff when needed."""
    for path, fields in [
        (STUDENTS_FILE, STUDENT_FIELDS),
        (STAFF_FILE, STAFF_FIELDS),
        (BOOKS_FILE, BOOK_FIELDS),
        (TRANSACTIONS_FILE, TRANSACTION_FIELDS),
    ]:
        if not path.exists():
            write_records(path, fields, [])

    staff = read_records(STAFF_FILE, STAFF_FIELDS)
    if not staff:
        staff.append({
            "username": "admin",
            "full_name": "Library Administrator",
            "password": hash_password("Library123!"),
        })
        write_records(STAFF_FILE, STAFF_FIELDS, staff)

    books = read_records(BOOKS_FILE, BOOK_FIELDS)
    if not books:
        books = [
            {
                "book_id": "B001", "title": "Introduction to Computing",
                "author": "Peter Norton", "category": "Computer Studies",
                "total_copies": "5", "available_copies": "5",
            },
            {
                "book_id": "B002", "title": "Python Programming for Beginners",
                "author": "John Smith", "category": "Programming",
                "total_copies": "4", "available_copies": "4",
            },
            {
                "book_id": "B003", "title": "Computer Networks",
                "author": "Andrew Tanenbaum", "category": "Networking",
                "total_copies": "3", "available_copies": "3",
            },
        ]
        write_records(BOOKS_FILE, BOOK_FIELDS, books)


def load_students():
    return read_records(STUDENTS_FILE, STUDENT_FIELDS)


def load_staff():
    return read_records(STAFF_FILE, STAFF_FIELDS)


def load_books():
    return read_records(BOOKS_FILE, BOOK_FIELDS)


def load_transactions():
    # Support older transaction files by adding missing fields in memory.
    records = read_records(TRANSACTIONS_FILE, TRANSACTION_FIELDS)
    changed = False
    for record in records:
        for field in TRANSACTION_FIELDS:
            if field not in record or record[field] is None:
                record[field] = ""
                changed = True
        if not record.get("fine_paid"):
            record["fine_paid"] = "0"
            changed = True
    if changed:
        write_records(TRANSACTIONS_FILE, TRANSACTION_FIELDS, records)
    return records


def save_students(records):
    return write_records(STUDENTS_FILE, STUDENT_FIELDS, records)


def save_staff(records):
    return write_records(STAFF_FILE, STAFF_FIELDS, records)


def save_books(records):
    return write_records(BOOKS_FILE, BOOK_FIELDS, records)


def save_transactions(records):
    return write_records(TRANSACTIONS_FILE, TRANSACTION_FIELDS, records)


def line():
    print("-" * 76)


def heading(title):
    print("\n" + "=" * 76)
    print(title.center(76))
    print("=" * 76)


def pause():
    input("\nPress Enter to continue...")


def money(amount):
    return f"₱{amount:,.2f}"


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def get_book(book_id, books=None):
    books = books if books is not None else load_books()
    for book in books:
        if book["book_id"].casefold() == book_id.casefold():
            return book
    return None


def get_student(student_id, students=None):
    students = students if students is not None else load_students()
    for student in students:
        if student["student_id"] == student_id:
            return student
    return None


def get_transaction(transaction_id, transactions=None):
    transactions = transactions if transactions is not None else load_transactions()
    for transaction in transactions:
        if transaction["transaction_id"] == transaction_id:
            return transaction
    return None


def next_id(prefix, records, field):
    highest = 0
    for record in records:
        value = record.get(field, "")
        if value.startswith(prefix):
            try:
                highest = max(highest, int(value[len(prefix):]))
            except ValueError:
                pass
    return f"{prefix}{highest + 1:04d}"


def calculate_fine(transaction, today=None):
    """Calculate unpaid fine based on return date or today for an unreturned book."""
    today = today or date.today()
    due_date = parse_date(transaction.get("due_date", ""))
    if not due_date:
        return 0, 0.0
    returned_date = parse_date(transaction.get("return_date", ""))
    end_date = returned_date or today
    overdue_days = max(0, (end_date - due_date).days)
    return overdue_days, overdue_days * FINE_PER_DAY


def outstanding_fine(transaction, today=None):
    _, total_fine = calculate_fine(transaction, today)
    paid = safe_float(transaction.get("fine_paid", "0"))
    return max(0.0, total_fine - paid)


def student_transactions(student_id):
    return [
        t for t in load_transactions()
        if t.get("student_id") == student_id
    ]


def display_books():
    heading("LIBRARY BOOK CATALOG")
    books = load_books()
    if not books:
        print("No books are currently listed.")
        return
    print(f"{'ID':<8} {'Title':<30} {'Author':<22} {'Available':>10}")
    line()
    for book in books:
        print(
            f"{book['book_id']:<8} {book['title'][:29]:<30} "
            f"{book['author'][:21]:<22} {book['available_copies']:>10}"
        )


def search_books():
    heading("SEARCH BOOKS")
    keyword = input("Enter a title, author, category, or book ID: ").strip().casefold()
    if not keyword:
        print("Please enter a search keyword.")
        return
    matches = [
        book for book in load_books()
        if keyword in " ".join([
            book.get("book_id", ""), book.get("title", ""),
            book.get("author", ""), book.get("category", "")
        ]).casefold()
    ]
    if not matches:
        print("No matching books found.")
        return
    for book in matches:
        line()
        print(f"Book ID          : {book['book_id']}")
        print(f"Title            : {book['title']}")
        print(f"Author           : {book['author']}")
        print(f"Category         : {book['category']}")
        print(f"Available copies : {book['available_copies']}")


def show_student_alerts(student_id):
    today = date.today()
    transactions = student_transactions(student_id)
    active = [
        t for t in transactions
        if t.get("status") in ("BORROWED", "RETURN_REQUESTED")
        and not t.get("return_date")
    ]
    alerts = []
    total_outstanding = 0.0

    for transaction in active:
        due = parse_date(transaction.get("due_date", ""))
        if due:
            days_until_due = (due - today).days
            overdue_days, fine = calculate_fine(transaction, today)
            outstanding = outstanding_fine(transaction, today)
            total_outstanding += outstanding
            book = get_book(transaction.get("book_id", ""))
            title = book["title"] if book else transaction.get("book_id", "Unknown book")
            if days_until_due == 0:
                alerts.append(f"DUE TODAY: {title}")
            elif 0 < days_until_due <= 2:
                alerts.append(f"DUE SOON ({days_until_due} day(s)): {title} — due {due.isoformat()}")
            elif overdue_days > 0:
                alerts.append(
                    f"OVERDUE: {title} — {overdue_days} day(s), "
                    f"fine {money(fine)}, outstanding {money(outstanding)}"
                )

    heading("YOUR LIBRARY ALERTS")
    if alerts:
        for alert in alerts:
            print(f"! {alert}")
    else:
        print("No books are due today, due soon, or overdue.")
    print(f"Total outstanding fine balance: {money(total_outstanding)}")


def student_view_records(student_id):
    heading("MY BORROWING RECORDS AND FINES")
    transactions = student_transactions(student_id)
    if not transactions:
        print("You do not have any borrowing records yet.")
        return

    today = date.today()
    total_outstanding = 0.0
    for transaction in transactions:
        book = get_book(transaction.get("book_id", ""))
        title = book["title"] if book else transaction.get("book_id", "Unknown book")
        overdue_days, total_fine = calculate_fine(transaction, today)
        paid = safe_float(transaction.get("fine_paid", "0"))
        outstanding = max(0.0, total_fine - paid)
        total_outstanding += outstanding
        print()
        line()
        print(f"Transaction ID : {transaction['transaction_id']}")
        print(f"Book           : {title}")
        print(f"Status         : {transaction['status']}")
        print(f"Request date   : {transaction.get('request_date', '-') or '-'}")
        print(f"Borrow date    : {transaction.get('borrow_date', '-') or '-'}")
        print(f"Due date       : {transaction.get('due_date', '-') or '-'}")
        print(f"Return date    : {transaction.get('return_date', '-') or 'Not returned'}")
        print(f"Overdue days   : {overdue_days}")
        print(f"Total fine     : {money(total_fine)}")
        print(f"Fine paid      : {money(paid)}")
        print(f"Outstanding    : {money(outstanding)}")
    line()
    print(f"TOTAL OUTSTANDING BALANCE: {money(total_outstanding)}")


def student_borrow_request(student_id):
    heading("REQUEST TO BORROW A BOOK")
    display_books()
    book_id = input("\nEnter the Book ID you want to borrow: ").strip()
    books = load_books()
    book = get_book(book_id, books)
    if not book:
        print("Book ID not found.")
        return
    try:
        available = int(book["available_copies"])
    except ValueError:
        available = 0
    if available <= 0:
        print("This book is currently unavailable.")
        return

    transactions = load_transactions()
    already_active = any(
        t.get("student_id") == student_id
        and t.get("book_id", "").casefold() == book_id.casefold()
        and t.get("status") in ("PENDING", "BORROWED", "RETURN_REQUESTED")
        and not t.get("return_date")
        for t in transactions
    )
    if already_active:
        print("You already have a pending request or active loan for this book.")
        return

    transaction_id = next_id("T", transactions, "transaction_id")
    transactions.append({
        "transaction_id": transaction_id,
        "student_id": student_id,
        "book_id": book["book_id"],
        "request_date": date.today().isoformat(),
        "borrow_date": "",
        "due_date": "",
        "return_date": "",
        "status": "PENDING",
        "fine_paid": "0",
    })
    if save_transactions(transactions):
        print(f"Borrowing request submitted. Request ID: {transaction_id}")
        print("A library staff member must approve your request before the book is borrowed.")


def student_return_request(student_id):
    heading("REQUEST TO RETURN A BOOK")
    transactions = load_transactions()
    active = [
        t for t in transactions
        if t.get("student_id") == student_id
        and t.get("status") == "BORROWED"
        and not t.get("return_date")
    ]
    if not active:
        print("You have no books eligible for a return request.")
        return

    for transaction in active:
        book = get_book(transaction["book_id"])
        title = book["title"] if book else transaction["book_id"]
        print(
            f"{transaction['transaction_id']} | {title} | "
            f"Due: {transaction.get('due_date') or 'Not set'}"
        )
    transaction_id = input("\nEnter the Transaction ID to return: ").strip().upper()
    transaction = get_transaction(transaction_id, transactions)
    if not transaction or transaction not in active:
        print("Invalid transaction ID.")
        return
    transaction["status"] = "RETURN_REQUESTED"
    if save_transactions(transactions):
        print("Return request recorded. Please hand the physical book to library staff.")
        print("The return date will be recorded after staff confirms receipt.")


def register_student():
    heading("STUDENT REGISTRATION")
    students = load_students()
    student_id = input("Student ID (format 02-2627-123456): ").strip()
    if not re.fullmatch(r"\d{2}-\d{4}-\d{6}", student_id):
        print("Invalid format. Use two digits, four digits, then six digits, separated by hyphens.")
        return
    if get_student(student_id, students):
        print("That Student ID is already registered.")
        return

    full_name = input("Full Name: ").strip()
    course = input("Course/Program: ").strip()
    year_level = input("Year Level (e.g., 1): ").strip()
    section = input("Section: ").strip()
    if not all([full_name, course, year_level, section]):
        print("All student information fields are required.")
        return

    password = input("Create Password (letters, numbers, and symbols allowed): ")
    if len(password) < 6:
        print("Password must contain at least 6 characters.")
        return
    confirm = input("Confirm Password: ")
    if password != confirm:
        print("Passwords do not match.")
        return

    students.append({
        "student_id": student_id,
        "full_name": full_name,
        "course": course,
        "year_level": year_level,
        "section": section,
        "password": hash_password(password),
    })
    if save_students(students):
        print("Registration successful. You may now log in.")


def student_login():
    heading("STUDENT LOGIN")
    student_id = input("Student ID: ").strip()
    password = input("Password: ")
    student = get_student(student_id)
    if not student or student["password"] != hash_password(password):
        print("Invalid Student ID or password.")
        pause()
        return
    print(f"\nWelcome, {student['full_name']}!")
    show_student_alerts(student_id)
    pause()
    student_menu(student)


def student_menu(student):
    while True:
        heading(f"STUDENT MENU — {student['full_name']}")
        print("1. View Book Catalog")
        print("2. Search Books")
        print("3. Request to Borrow a Book")
        print("4. View My Borrowing Records and Fines")
        print("5. Request to Return a Book")
        print("6. View Due-Date and Fine Alerts")
        print("0. Log Out")
        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            display_books()
            pause()
        elif choice == "2":
            search_books()
            pause()
        elif choice == "3":
            student_borrow_request(student["student_id"])
            pause()
        elif choice == "4":
            student_view_records(student["student_id"])
            pause()
        elif choice == "5":
            student_return_request(student["student_id"])
            pause()
        elif choice == "6":
            show_student_alerts(student["student_id"])
            pause()
        elif choice == "0":
            print("You have been logged out.")
            break
        else:
            print("Invalid choice. Please try again.")
            pause()


def staff_login():
    heading("LIBRARY / STAFF LOGIN")
    username = input("Username: ").strip()
    password = input("Password: ")
    for staff in load_staff():
        if staff["username"].casefold() == username.casefold() and staff["password"] == hash_password(password):
            print(f"\nWelcome, {staff['full_name']}!")
            pause()
            staff_menu(staff)
            return
    print("Invalid username or password.")
    pause()


def staff_add_book():
    heading("ADD A BOOK")
    books = load_books()
    book_id = input("New Book ID (e.g., B004): ").strip().upper()
    if not re.fullmatch(r"[A-Z0-9-]+", book_id):
        print("Use letters, numbers, and hyphens for the Book ID.")
        return
    if get_book(book_id, books):
        print("That Book ID already exists.")
        return
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    category = input("Category: ").strip()
    try:
        copies = int(input("Number of copies: ").strip())
        if copies < 1:
            raise ValueError
    except ValueError:
        print("Number of copies must be a positive whole number.")
        return
    if not all([title, author, category]):
        print("Title, author, and category are required.")
        return
    books.append({
        "book_id": book_id, "title": title, "author": author,
        "category": category, "total_copies": str(copies),
        "available_copies": str(copies),
    })
    if save_books(books):
        print("Book added successfully.")


def staff_process_borrowing():
    heading("PROCESS BORROWING REQUESTS")
    transactions = load_transactions()
    pending = [t for t in transactions if t.get("status") == "PENDING"]
    if not pending:
        print("There are no pending borrowing requests.")
        return
    students = load_students()
    books = load_books()
    for t in pending:
        student = get_student(t["student_id"], students)
        book = get_book(t["book_id"], books)
        print(
            f"{t['transaction_id']} | Student: {student['full_name'] if student else t['student_id']} "
            f"| Book: {book['title'] if book else t['book_id']} "
            f"| Requested: {t.get('request_date', '-')}"
        )
    transaction_id = input("\nEnter Transaction ID to process (or press Enter to cancel): ").strip().upper()
    if not transaction_id:
        return
    transaction = get_transaction(transaction_id, transactions)
    if not transaction or transaction not in pending:
        print("Invalid transaction ID.")
        return
    action = input("Approve request? (A=Approve, R=Reject, C=Cancel): ").strip().upper()
    if action == "A":
        book = get_book(transaction["book_id"], books)
        if not book or int(book["available_copies"] or 0) <= 0:
            print("No available copies. Request cannot be approved.")
            return
        book["available_copies"] = str(int(book["available_copies"]) - 1)
        today = date.today()
        transaction["borrow_date"] = today.isoformat()
        transaction["due_date"] = (today + timedelta(days=BORROWING_DAYS)).isoformat()
        transaction["status"] = "BORROWED"
        if save_books(books) and save_transactions(transactions):
            print("Request approved.")
            print(f"Borrow date: {today.isoformat()}")
            print(f"Due date   : {transaction['due_date']}")
            print(f"Borrowing period: {BORROWING_DAYS} calendar days.")
    elif action == "R":
        transaction["status"] = "REJECTED"
        if save_transactions(transactions):
            print("Borrowing request rejected.")
    elif action == "C":
        print("No changes made.")
    else:
        print("Invalid action.")


def staff_confirm_return():
    heading("CONFIRM BOOK RETURNS")
    transactions = load_transactions()
    requests = [t for t in transactions if t.get("status") == "RETURN_REQUESTED"]
    if not requests:
        print("There are no return requests waiting for confirmation.")
        return
    students = load_students()
    for t in requests:
        student = get_student(t["student_id"], students)
        book = get_book(t["book_id"])
        overdue_days, fine = calculate_fine(t)
        print(
            f"{t['transaction_id']} | {student['full_name'] if student else t['student_id']} "
            f"| {book['title'] if book else t['book_id']} "
            f"| Due: {t.get('due_date', '-')} | Fine as of today: {money(fine)} "
            f"({overdue_days} overdue day(s))"
        )
    transaction_id = input("\nEnter Transaction ID after physically receiving the book: ").strip().upper()
    transaction = get_transaction(transaction_id, transactions)
    if not transaction or transaction not in requests:
        print("Invalid transaction ID.")
        return
    confirm = input("Confirm that the physical book has been received? (Y/N): ").strip().upper()
    if confirm != "Y":
        print("Return not confirmed.")
        return

    transaction["return_date"] = date.today().isoformat()
    transaction["status"] = "RETURNED"
    books = load_books()
    book = get_book(transaction["book_id"], books)
    if book:
        book["available_copies"] = str(int(book["available_copies"] or 0) + 1)
        book["total_copies"] = str(max(int(book["total_copies"] or 0), int(book["available_copies"])))
    saved_books = save_books(books)
    saved_transactions = save_transactions(transactions)
    if saved_books and saved_transactions:
        overdue_days, fine = calculate_fine(transaction)
        paid = safe_float(transaction.get("fine_paid", "0"))
        print(f"Return confirmed on {transaction['return_date']}.")
        print(f"Overdue days : {overdue_days}")
        print(f"Total fine   : {money(fine)}")
        print(f"Fine paid    : {money(paid)}")
        print(f"Outstanding  : {money(max(0.0, fine - paid))}")


def staff_overdue_report():
    heading("OVERDUE BOOKS REPORT")
    today = date.today()
    transactions = load_transactions()
    overdue = []
    for t in transactions:
        if t.get("status") in ("BORROWED", "RETURN_REQUESTED") and not t.get("return_date"):
            days, fine = calculate_fine(t, today)
            if days > 0:
                overdue.append((t, days, fine))
    if not overdue:
        print("No books are currently overdue.")
        return

    students = load_students()
    print(f"{'Transaction':<14} {'Student ID':<17} {'Book ID':<9} {'Days':>5} {'Fine':>12} {'Outstanding':>14}")
    line()
    for t, days, fine in overdue:
        paid = safe_float(t.get("fine_paid", "0"))
        outstanding = max(0.0, fine - paid)
        print(
            f"{t['transaction_id']:<14} {t['student_id']:<17} {t['book_id']:<9} "
            f"{days:>5} {money(fine):>12} {money(outstanding):>14}"
        )
        student = get_student(t["student_id"], students)
        if student:
            print(f"    Student: {student['full_name']}")
    line()
    print(f"Overdue loans: {len(overdue)}")


def staff_record_fine_payment():
    heading("RECORD FINE PAYMENT")
    transactions = load_transactions()
    candidates = []
    for t in transactions:
        _, total_fine = calculate_fine(t)
        paid = safe_float(t.get("fine_paid", "0"))
        outstanding = max(0.0, total_fine - paid)
        if outstanding > 0:
            candidates.append((t, total_fine, paid, outstanding))
    if not candidates:
        print("There are no outstanding fines at this time.")
        return

    for t, total_fine, paid, outstanding in candidates:
        student = get_student(t["student_id"])
        book = get_book(t["book_id"])
        print(
            f"{t['transaction_id']} | {student['full_name'] if student else t['student_id']} "
            f"| {book['title'] if book else t['book_id']} "
            f"| Fine: {money(total_fine)} | Paid: {money(paid)} "
            f"| Outstanding: {money(outstanding)}"
        )
    transaction_id = input("\nEnter Transaction ID for payment: ").strip().upper()
    selected = next((item for item in candidates if item[0]["transaction_id"] == transaction_id), None)
    if not selected:
        print("Invalid transaction ID or no outstanding balance.")
        return
    transaction, total_fine, paid, outstanding = selected
    try:
        amount = float(input(f"Payment amount (maximum {money(outstanding)}): ₱").strip())
        if amount <= 0 or amount > outstanding + 0.00001:
            raise ValueError
    except ValueError:
        print("Invalid amount. Payment must be greater than zero and cannot exceed the outstanding balance.")
        return
    transaction["fine_paid"] = f"{paid + amount:.2f}"
    if save_transactions(transactions):
        print(f"Payment of {money(amount)} recorded successfully.")
        print(f"Remaining balance: {money(max(0.0, outstanding - amount))}")



def staff_fine_report():
    """Display all transactions that have a fine or a recorded fine payment."""
    heading("FINE MANAGEMENT REPORT")
    transactions = load_transactions()
    today = date.today()
    fine_records = []

    for transaction in transactions:
        overdue_days, total_fine = calculate_fine(transaction, today)
        paid = safe_float(transaction.get("fine_paid", "0"))
        outstanding = max(0.0, total_fine - paid)

        if total_fine > 0 or paid > 0:
            fine_records.append(
                (transaction, overdue_days, total_fine, paid, outstanding)
            )

    if not fine_records:
        print("No fine records or fine payments are available.")
        return

    print(
        f"{'Transaction':<13} {'Student ID':<17} {'Book ID':<8} "
        f"{'Days':>4} {'Total Fine':>12} {'Paid':>12} {'Balance':>12}"
    )
    line()

    for transaction, days, total_fine, paid, outstanding in fine_records:
        print(
            f"{transaction['transaction_id']:<13} "
            f"{transaction['student_id']:<17} "
            f"{transaction['book_id']:<8} "
            f"{days:>4} {money(total_fine):>12} "
            f"{money(paid):>12} {money(outstanding):>12}"
        )
        if outstanding <= 0 and total_fine > 0:
            status_label = "PAID"
        elif paid > 0:
            status_label = "PARTIALLY PAID"
        else:
            status_label = "UNPAID"
        print(f"    Fine status: {status_label}")

    line()
    total_fines = sum(record[2] for record in fine_records)
    total_paid = sum(record[3] for record in fine_records)
    total_outstanding = sum(record[4] for record in fine_records)
    print(f"Total fines calculated : {money(total_fines)}")
    print(f"Total payments recorded: {money(total_paid)}")
    print(f"Total outstanding      : {money(total_outstanding)}")

def staff_summary():
    heading("LIBRARY SUMMARY")
    books = load_books()
    students = load_students()
    transactions = load_transactions()
    today = date.today()
    total_copies = sum(int(b.get("total_copies") or 0) for b in books)
    available_copies = sum(int(b.get("available_copies") or 0) for b in books)
    borrowed = sum(1 for t in transactions if t.get("status") in ("BORROWED", "RETURN_REQUESTED"))
    pending = sum(1 for t in transactions if t.get("status") == "PENDING")
    overdue_count = 0
    total_fines = 0.0
    total_paid = 0.0
    outstanding_total = 0.0

    for t in transactions:
        days, fine = calculate_fine(t, today)
        if days > 0 and t.get("status") in ("BORROWED", "RETURN_REQUESTED", "RETURNED"):
            overdue_count += 1
        paid = safe_float(t.get("fine_paid", "0"))
        total_fines += fine
        total_paid += paid
        outstanding_total += max(0.0, fine - paid)

    print(f"Registered students       : {len(students)}")
    print(f"Book titles in catalog    : {len(books)}")
    print(f"Total physical copies     : {total_copies}")
    print(f"Available copies           : {available_copies}")
    print(f"Currently borrowed         : {borrowed}")
    print(f"Pending borrow requests    : {pending}")
    print(f"Overdue transactions       : {overdue_count}")
    print(f"Calculated fines           : {money(total_fines)}")
    print(f"Payments recorded          : {money(total_paid)}")
    print(f"Outstanding fine balances  : {money(outstanding_total)}")


def staff_menu(staff):
    while True:
        heading(f"LIBRARY STAFF MENU — {staff['full_name']}")
        print("1. View Book Catalog")
        print("2. Add a Book")
        print("3. Process Borrowing Requests")
        print("4. Confirm Physical Book Returns")
        print("5. View Overdue Books Report")
        print("6. Record Fine Payment")
        print("7. View Library Summary")
        print("8. View Fine Management Report")
        print("0. Log Out")
        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            display_books()
            pause()
        elif choice == "2":
            staff_add_book()
            pause()
        elif choice == "3":
            staff_process_borrowing()
            pause()
        elif choice == "4":
            staff_confirm_return()
            pause()
        elif choice == "5":
            staff_overdue_report()
            pause()
        elif choice == "6":
            staff_record_fine_payment()
            pause()
        elif choice == "7":
            staff_summary()
            pause()
        elif choice == "8":
            staff_fine_report()
            pause()
        elif choice == "0":
            print("You have been logged out.")
            break
        else:
            print("Invalid choice. Please try again.")
            pause()


def main():
    ensure_data_files()
    while True:
        heading("LIBRAPAY: AUTOMATED LIBRARY FINE MANAGEMENT")
        # Date/time terminal display intentionally removed.
        print("1. Student Registration")
        print("2. Student Login")
        print("3. Library / Staff Login")
        print("0. Exit")
        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            register_student()
            pause()
        elif choice == "2":
            student_login()
        elif choice == "3":
            staff_login()
        elif choice == "0":
            print("\nThank you for using LibraPay. Goodbye!")
            break
        else:
            print("Invalid choice. Please choose 0, 1, 2, or 3.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")
