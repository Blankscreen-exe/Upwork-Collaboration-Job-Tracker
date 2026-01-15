# Upwork Tracker

A locally hosted web application to track Upwork jobs, worker allocations/splits, connect investment deductions, and payouts.

## Features

- **Manage Workers**: Create, update, archive workers with auto-generated codes (W01, W02, etc.)
- **Manage Jobs**: Track Upwork jobs with identifiers, connects used, and auto-generated codes (J01, J02, etc.)
- **Record Receipts**: Add multiple income entries per job (milestones, weekly payments, bonuses)
- **Edit Receipts**: Update receipt details after creation
- **Define Worker Allocations**: Set percent or fixed amount splits per job
- **Auto-Generated Payments**: Payments are automatically created when receipts are added, based on worker allocations
- **Manual Payments**: Create and edit payments manually
- **Payment Status Tracking**: Mark payments as paid/unpaid to track actual disbursements vs. calculated amounts
- **Dashboard Summaries**: View totals for received, connect deductions, platform fees, paid amounts, and dues
- **Versioned Settings**: Settings changes affect only new jobs (historical calculations remain unchanged)
- **Optional Job Finalization**: Snapshot calculations for audit stability

## Tech Stack

- FastAPI
- Jinja2 (server-side rendering)
- Bootstrap 5
- SQLite
- SQLAlchemy ORM
- Alembic migrations

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file (copy from `.env.example`):
   ```
   ADMIN_PASSWORD=admin123
   DATABASE_URL=sqlite:///./upwork_tracker.db
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Create an initial settings version:
   - Start the application
   - Navigate to Settings
   - Create a new settings version with default rules
   - Activate it

5. Run the application:
   ```bash
   python main.py
   ```
   
   Or with uvicorn:
   ```bash
   uvicorn main:app --reload
   ```

6. Access the application at `http://localhost:8000`

## Default Settings JSON

When creating your first settings version, use this as a starting point:

```json
{
  "currency_default": "USD",
  "connect_cost_per_unit": 0.15,
  "platform_fee": {
    "enabled": false,
    "mode": "percent",
    "value": 0.10,
    "apply_on": "net"
  },
  "rounding": {
    "mode": "2dp"
  },
  "require_percent_allocations_sum_to_1": true
}
```

### Settings Explanation

- **`connect_cost_per_unit`**: Cost per connect in dollars (e.g., 0.15 = $0.15 per connect)
- **`platform_fee`**: Optional admin cut (can be percent or fixed, applied on gross or net)
- **`require_percent_allocations_sum_to_1`**: If true, percent allocations must sum to 1.0 (allows partial sums during creation, but errors if exceeds 1.0)

## How It Works

### Connect Deduction Calculation

Connect deductions are calculated based on the number of connects used per job:
- When creating/editing a job, enter the number of connects used
- Connect deduction = `connects_used × connect_cost_per_unit`
- Example: 10 connects × $0.15 = $1.50 deduction

### Payment Generation

When you add a receipt to a job:
1. The system calculates deductions (connects + platform fee)
2. Determines net distributable amount
3. Automatically creates payment entries for each worker allocation
4. Payments are marked as "auto-generated" and "unpaid" by default
5. You can then mark them as paid when you actually disburse funds

### Payment Tracking

- **Earned**: Amount calculated from allocations
- **Paid**: Amount from payments marked as `is_paid = true`
- **Due**: Earned - Paid

This allows you to track what workers have earned vs. what you've actually paid them.

## Project Structure

```
.
├── alembic/              # Database migrations
├── app/
│   ├── routers/          # Route handlers
│   ├── services/         # Business logic (calculations)
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # Database setup
│   ├── config.py         # Configuration
│   └── dependencies.py   # Dependency injection
├── templates/            # Jinja2 templates
├── main.py              # FastAPI application entry point
└── requirements.txt     # Python dependencies
```

## Important Notes

- **Settings Versions**: Immutable. To modify settings, clone an existing version and activate it.
- **Job Settings**: Jobs are automatically linked to the active settings version when created.
- **Historical Calculations**: Changing settings only affects new jobs (unless manually reassigned).
- **Finalized Jobs**: Use snapshot calculations and cannot be edited until unfinalized.
- **Precision**: All calculations use Decimal arithmetic for financial accuracy.
- **Auto-Generated Payments**: Payments created from receipts are preserved even if receipts are deleted (for historical tracking).
- **Payment History**: Deleting a receipt does NOT delete associated payments to maintain payment history.
- **Allocation Validation**: Percent allocations can be created incrementally, but cannot exceed 1.0 total.

## Troubleshooting

### PDF Generation Issues (GTK Runtime on Windows)

If you encounter errors when generating PDF invoices (e.g., "cannot load library 'gobject-2.0-0'"), you need to install the GTK+ runtime libraries for Windows.

#### Solution 1: Install GTK3 Runtime

1. **Download GTK3 Runtime:**
   - Visit: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
   - Download the latest GTK3 runtime installer (e.g., `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe`)

2. **Install GTK3 Runtime:**
   - Run the installer
   - Install to the default location (typically `C:\Program Files\GTK3-Runtime Win64\`)

3. **Add to System PATH (Optional but Recommended):**
   - Open System Properties → Environment Variables
   - Edit the `Path` variable
   - Add: `C:\Program Files\GTK3-Runtime Win64\bin` (or your installation path)
   - Click OK and restart your terminal/PowerShell

4. **Restart the Application:**
   - Close and restart your terminal/PowerShell
   - Restart the application

#### Solution 2: Verify GTK Installation

To check if GTK is properly installed and accessible:

```powershell
# Check if GTK DLLs exist
Test-Path "C:\Program Files\GTK3-Runtime Win64\bin\gobject-2.0-0.dll"

# Or check your installation path
Get-ChildItem "C:\Program Files\GTK3-Runtime Win64\bin\*.dll" | Select-Object Name
```

#### Solution 3: Manual PATH Configuration

If GTK is installed but not detected automatically:

1. **Find your GTK installation path** (common locations):
   - `C:\Program Files\GTK3-Runtime Win64\bin`
   - `C:\gtk3-runtime-3.24.31-2022-01-04-ts-win64\bin`
   - `C:\GTK\bin`

2. **Add to System PATH:**
   - Open System Properties → Environment Variables
   - Add the `bin` folder path to your system PATH
   - Restart your terminal

#### Solution 4: Application Auto-Detection

The application automatically searches for GTK in common installation locations. If GTK is installed in a non-standard location:

1. Add the GTK `bin` folder to your system PATH
2. Restart the application
3. The application will detect it automatically

#### Common Errors

- **"cannot load library 'gobject-2.0-0'"**: GTK runtime is not installed or not in PATH
- **"PDF generation is not available"**: WeasyPrint cannot find GTK dependencies
- **"Error 0x7e"**: Missing or corrupted GTK DLL files

#### Alternative: Disable PDF Generation

If you don't need PDF generation, the application will run normally without GTK. PDF generation features will simply be unavailable, but all other features work fine.

#### Additional Resources

- [WeasyPrint Installation Guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
- [WeasyPrint Troubleshooting](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting)
- [GTK for Windows Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)