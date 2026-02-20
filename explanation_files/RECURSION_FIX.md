# 🔧 Fixed: Recursion Error in Streamlit App

## Problem
The Streamlit app was getting a `RecursionError: maximum recursion depth exceeded` due to incorrect import paths after the folder structure was reorganized into a `tests/` directory.

## Solution Applied

### 1. **Fixed Import Paths**

#### Streamlit App ([tests/streamlit_test/app.py](tests/streamlit_test/app.py))
```python
# OLD (incorrect):
backend_path = Path(__file__).parent.parent  # This pointed to tests/ instead of backend/

# NEW (correct):
backend_path = Path(__file__).parent.parent.parent  # Now correctly points to backend/
```

#### Test Scripts ([tests/test_files/](tests/test_files/))
Both `test_analysis.py` and `test_multi_day_analysis.py` were updated:
```python
# Added sys.path setup
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Fixed test_data path
# OLD: Path(__file__).parent / "test_data" / filename
# NEW: Path(__file__).parent.parent / "test_data" / filename
```

## ✅ How to Run Everything Now

### Current Folder Structure
```
backend/
├── app/                           # Main application code
│   ├── agents/
│   ├── graph/
│   ├── services/
│   └── main.py
├── tests/                         # All test files (NEW location)
│   ├── streamlit_test/
│   │   └── app.py
│   ├── test_data/                 # Sample JSON files
│   │   ├── user1_day1.json
│   │   ├── user1_day2.json
│   │   ├── user1_day3.json
│   │   └── ...
│   └── test_files/
│       ├── test_analysis.py
│       └── test_multi_day_analysis.py
├── venv/
└── requirements.txt
```

### Commands (Run from `backend/` directory)

#### 1. Run Streamlit Dashboard
```bash
streamlit run tests/streamlit_test/app.py
```

#### 2. Run Single-Day Analysis Test
```bash
python tests/test_files/test_analysis.py
```

#### 3. Run Multi-Day Analysis Test
```bash
python tests/test_files/test_multi_day_analysis.py
```

#### 4. Start FastAPI Server
```bash
uvicorn app.main:app --reload
```

#### 5. Test API Endpoints
```bash
# Single day
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @tests/test_data/user1_day1.json

# Multi-day  
curl -X POST http://localhost:8000/analyze/multi-day \
  -H "Content-Type: application/json" \
  -d '{"days": [...]}'
```

## 🔍 What Was Wrong

The recursion error occurred because:

1. **File Structure Changed**: The `tests/` folder was created, moving files from:
   - `backend/streamlit_test/` → `backend/tests/streamlit_test/`
   - `backend/test_data/` → `backend/tests/test_data/`
   - `backend/test_*.py` → `backend/tests/test_files/`

2. **Import Paths Not Updated**: The Python files still had old paths that assumed they were directly under `backend/`, causing:
   - Wrong directory added to `sys.path`
   - Python looking for the `app` package in the wrong location
   - The script file named `app.py` conflicting with the `app` package
   - Circular import loop → recursion error

3. **Fix Applied**: Updated all `Path(__file__).parent` calculations to correctly navigate to the `backend/` directory from the new `tests/` subdirectories.

## ✅ All Fixed Files

- ✅ [tests/streamlit_test/app.py](tests/streamlit_test/app.py) - Fixed backend_path
- ✅ [tests/test_files/test_analysis.py](tests/test_files/test_analysis.py) - Fixed imports and data path
- ✅ [tests/test_files/test_multi_day_analysis.py](tests/test_files/test_multi_day_analysis.py) - Fixed imports and data path
- ✅ [tests/test_data/README.md](tests/test_data/README.md) - Updated run commands

## 🚀 Ready to Use!

You can now run the Streamlit app without recursion errors:
```bash
streamlit run tests/streamlit_test/app.py
```
