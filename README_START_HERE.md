# Complaint Support — Django + DRF + React + SQLite

## What is included
- Customer/staff/admin login, registration, permissions and password hashing.
- Seven default categories; learned category, priority and sentiment models.
- Automatic department routing, manual staff assignment and human review.
- Six statuses, complaint conversations, history and in-app notifications.
- Owner edit and soft delete for Submitted/unassigned complaints; edit re-analyzes text.
- Evidence uploads: PDF/PNG/JPEG, max 5 MB each, 3 per complaint. Private authenticated downloads.
- Admin department/category creation, enable/disable and routing changes. Existing names update records; renaming is not included to protect historical labels. Add training examples to automatically recognize a new category.
- User role/department/active management, search/status filters, counts and CSV export.
- Responsive CSS throughout: sidebar navigation, cards, tables, forms, login and mobile layout.
- TF-IDF + logistic regression via scikit-learn. Priority also has urgent-keyword escalation. FAQ assistant uses TF-IDF cosine-similarity retrieval; it is not an LLM.
- Training and separate evaluation CSVs, evaluation script with accuracy, precision, recall, F1 and confusion matrix, measured inference latency and saved JSON report.

## Existing project update — easiest method
Stop backend and frontend with Ctrl+C first. Extract ZIP to Downloads, then double-click `INSTALL_UPDATE.cmd` beside this file. It uses your existing Desktop project at `Ai-based-complaint-support-system\ai_complaint_system`, backs up existing code/database, copies new code, installs backend dependencies, and migrates SQLite. It never copies a database from this package. Read the console result; an error stops the update.
If your existing folder is elsewhere: open terminal here and run `py update_project.py "FULL EXISTING ai_complaint_system PATH"`.
Then start backend and frontend using commands below. This script does NOT publish or use GitHub.

## Manual update instead
Backup existing project. Copy this package's backend/frontend folders into your existing ai_complaint_system folder, choose Replace files, and MERGE without deleting existing folders. Preserve backend/db.sqlite3, backend/.venv, backend/private_media and frontend/node_modules.
Backend folder: install requirements again (scikit-learn is new) and run migrate.

## Run backend — Windows PowerShell
```powershell
cd "C:\Users\hp\Desktop\Ai-based-complaint-support-system\ai_complaint_system\backend"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```
For an existing installation do not recreate .venv; seed_demo is optional and doesn't reset existing passwords.

## Run frontend — second terminal
```powershell
cd "C:\Users\hp\Desktop\Ai-based-complaint-support-system\ai_complaint_system\frontend"
npm install
npm run dev
```
Open http://127.0.0.1:5173 and Ctrl+F5. Keep both servers running.
Accounts: admin / staff / customer. Password: DemoPass123!
Demo staff belongs to IT Support. Other department staff can be created by registering a new user and changing its role/department through admin Users.
Python 3.12+ and Node.js 22+ recommended. No paid API key or ChatGPT API required.

## Test walkthrough
1. Customer: submit a technical complaint; attach a genuine PNG/PDF; download it.
2. Edit title/details before assignment, check changed analysis/history.
3. Delete a separate test complaint; confirm it disappears; Cancel should retain it.
4. Admin: assign IT Support staff and change to Assigned.
5. Staff: reply, set In Progress then Resolved.
6. Customer: check response/history/notification; edit/delete unavailable after assignment.
7. Admin Settings: add a department; update a category's department by entering the same category name. New complaints route there, existing complaints retain historical routing.
8. Admin Users: set a registered user to staff with the new department.
9. FAQ: ask tracking/payment/internet questions; unsupported questions fall back to submission guidance.
10. Admin: export CSV; compare rows with active complaints. Resize browser to mobile width.

## Automated verification
Backend: `python manage.py test` (7 workflow/permission/upload/configuration tests).
Frontend: `npm run build`.
Evaluation: from backend `python evaluate.py`, or pass a representative category CSV path. Script writes evaluation_report.json. Evaluation data must not overlap exact training texts.

## Dataset and research limitations — use these in viva/report
140 manually authored category training examples (20 per category across 7 categories). Category evaluation used 70 manually prepared English examples, with 68/70 correct predictions (97.14% sample accuracy) and 97.20% macro F1. Priority and sentiment each achieved 100% on only 10 manually authored evaluation examples. These are small demonstration datasets, not representative real-world benchmarks. Evaluation examples were previously inspected during model improvement, so the category result is not an independent benchmark. No real customer data was collected. Staff must review AI predictions.
Category sample evaluation: 68/70 correct (97.14% accuracy; 97.20% macro F1) on manually authored English examples. This is not an independent or representative real-world benchmark. Priority and sentiment each scored 10/10 on small manually authored test sets.
Staff should review outputs. Negation, subtle sentiment, mixed issues and unfamiliar wording may fail. English only, as permitted by the proposal's initial scope. Model probability is not calibrated accuracy.
The chatbot retrieves fixed answers and cannot perform refunds, financial actions or autonomous sensitive decisions. New categories need training rows and server restart to participate in automatic classification. Default category routing is database configurable.

## Proposal alignment and remaining academic work
See PROPOSAL_ALIGNMENT.md. SQLite is the user's chosen replacement for MySQL/PostgreSQL. No external email/SMS was specified; notifications are in-app. BERT is a literature reference, not a mandatory model. Selected scikit-learn/NumPy dependencies cover implemented techniques; every listed optional library is not necessary.
This package is a feature-complete local demonstration for the described core functional workflow, not a validated production deployment or completed thesis. Real user satisfaction/usability feedback, representative data validation, literature verification, institution-specific acceptance and thesis/presentation remain human academic work. A testing/feedback template is included; results are not invented.

## Deployment / data
Development server and localhost token authentication only. Public deployment requires HTTPS, environment secret, DEBUG off, proper hosts/CORS and production server. Files are downloaded through authorized API endpoints, not public media URLs. File signature/size validation is basic, not antivirus scanning. Uploads and database must be backed up together.
An existing archived complaint remains archived. Old model wording/results on historical complaints remain until edited. Demo admin is a React role; for Django admin use `python manage.py createsuperuser`.
