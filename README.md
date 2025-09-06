# How to Run the API from the CODE Directory

1. Change to the CODE directory:
	```bash
	cd CODE
	```

2. Activate the virtual environment:
	```bash
	source .venv/bin/activate
	```

3. Start the API server:
	```bash
	python -m uvicorn main:app --reload
	```

You should see output similar to:
```
INFO:     Will watch for changes in these directories: ['/home/mgauthier/Documents/GitHub/Conversational-interface-for-study-planning/CODE']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [19030] using StatReload
INFO:     Started server process [19032]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```
# Conversational interface for study planning
 Final Degree Project: ORT University
