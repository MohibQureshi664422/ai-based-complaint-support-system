# Proposal alignment
| Proposal requirement | Implementation |
|---|---|
| Registration/login, three roles | Django user hashing, DRF token auth, role-specific querysets and actions |
| Submission, supporting files, unique ID | Complaint fields + private PDF/image upload/download + database ID |
| Seven default categories | TF-IDF logistic regression; database-managed labels/routing |
| Priority detection | Learned 3-class classifier + safety keyword escalation |
| Basic sentiment | Learned Positive/Neutral/Negative classifier |
| Department/staff assignment | Category mapping to department; admin assigns active matching staff |
| FAQ chatbot/troubleshooting | NLP similarity retrieval over curated FAQ guidance, fallback for unsupported questions |
| Six tracking statuses | Submitted, Under Review, Assigned, In Progress, Resolved, Closed |
| Dashboard, users/departments/categories | React role dashboards, admin Users and Settings, counts/search/filter/CSV |
| Notifications/history | In-app notifications on submission/edit/upload/review/reply, timestamped history |
| Evaluation | Independent small sample CSVs, metrics JSON, inference timing, automated tests |
| Usability/user satisfaction | Real participant testing still required; included form has blank results |
| SQL database | SQLite by user request; differs from originally listed MySQL/PostgreSQL |
| Documentation/presentation | README, test steps and alignment supplied; formal institution thesis/slides not claimed complete |
| Outside scope | No automatic refunds/legal decisions/voice/general-purpose organizational integrations |

Settings support record creation, routing changes and activation states by stable name. Category recognition for new labels requires adding training examples and restarting the backend. Existing historical records are retained; no general-purpose rename/delete operation rewrites history.

Academic diagrams: tables are Django User -> Profile (one-to-one), User -> Complaint (owner), User -> Complaint (assigned staff), Complaint -> Message/History/Notification/Attachment, Department -> Category. React calls DRF; DRF checks permissions, runs ML inference and stores results in SQLite. All inference runs locally; no ChatGPT API.
