import streamlit as st
import pandas as pd
from datetime import datetime, time
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Canteen Meal Management", layout="wide")
st.title("🍽️ Canteen Meal Management System")

# Define meal time windows
lunch_start = time(13, 0)
lunch_end = time(16, 0)
dinner_start = time(19, 0)
dinner_end = time(22, 0)

def classify_meal(punch_time):
    t = punch_time.time()
    if lunch_start <= t <= lunch_end:
        return "Lunch"
    elif dinner_start <= t <= dinner_end:
        return "Dinner"
    else:
        return None

# Upload new employee data
st.sidebar.header("👥 Upload New Employees")
employee_file = st.sidebar.file_uploader("Upload Employee List (Excel or TXT)", type=["xlsx", "xls", "txt"], key="employee")

emp_df = pd.DataFrame()

if employee_file:
    if employee_file.name.endswith(".txt"):
        emp_df = pd.read_csv(employee_file, delimiter="\t")
    else:
        emp_df = pd.read_excel(employee_file)

    expected_emp_cols = ["Employee ID", "Join Date", "Section"]
    if not all(col in emp_df.columns for col in expected_emp_cols):
        st.sidebar.error(f"Employee file must contain columns: {expected_emp_cols}")
    else:
        st.sidebar.success("✅ Employee list uploaded")
        st.sidebar.dataframe(emp_df)

uploaded_file = st.file_uploader("📤 Upload Punch Data (Excel or TXT)", type=["xlsx", "xls", "txt"])

if uploaded_file:
    if uploaded_file.name.endswith(".txt"):
        df = pd.read_csv(uploaded_file, delimiter="\t")
    else:
        df = pd.read_excel(uploaded_file)

    expected_columns = ["Employee ID", "Punch Time"]
    if not all(col in df.columns for col in expected_columns):
        st.error(f"Punch file must contain columns: {expected_columns}")
    else:
        df["Punch Time"] = pd.to_datetime(df["Punch Time"])
        df["Date"] = df["Punch Time"].dt.date
        df["Meal"] = df["Punch Time"].apply(classify_meal)

        meal_df = df[df["Meal"].notna()].copy()

        st.success("✅ Data processed successfully!")

        if not emp_df.empty:
            meal_df = meal_df.merge(emp_df, on=["Employee ID"], how="left")

        st.subheader("🔍 Individual Report")
        employee_id = st.text_input("Enter Employee ID")

        if employee_id:
            personal_df = meal_df[meal_df["Employee ID"].astype(str) == employee_id]
            if not personal_df.empty:
                summary = personal_df.groupby(["Date", "Meal"]).size().unstack(fill_value=0)
                summary["Total Meals"] = summary.sum(axis=1)

                all_dates = pd.date_range(summary.index.min(), summary.index.max(), freq='D').date
                total_days = len(all_dates)
                present_days = summary.shape[0]
                attendance_pct = round((present_days / total_days) * 100, 2)
                avg_meal_per_day = round(summary["Total Meals"].sum() / total_days, 2)

                st.write("### 🍽️ Personal Meal Report")
                employee_info = personal_df[["Employee ID", "Join Date", "Section"]].drop_duplicates()
                st.write("#### 👤 Employee Info:")
                st.dataframe(employee_info)
                st.dataframe(summary)

                st.info(f"📆 Total Days: {total_days}, Present Days: {present_days}, Attendance: {attendance_pct}%")
                st.info(f"📊 Average Meals per Day: {avg_meal_per_day}")

                non_eating_days = sorted(set(all_dates) - set(summary.index))
                if non_eating_days:
                    st.write("### ❌ Non-Eating Days")
                    st.write(non_eating_days)

                export_df = summary.copy()
                export_df.insert(0, "Employee ID", employee_id)
                export_df.insert(1, "Join Date", employee_info.iloc[0]["Join Date"])
                export_df.insert(2, "Section", employee_info.iloc[0]["Section"])
                csv = export_df.to_csv().encode("utf-8")
                st.download_button("📥 Download Personal Report (CSV)", csv, "personal_report.csv", "text/csv")

                # PDF export
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Personal Meal Report", ln=True, align="C")
                for index, row in employee_info.iterrows():
                    pdf.cell(200, 10, txt=f"ID: {row['Employee ID']} | Join: {row['Join Date']} | Section: {row['Section']}", ln=True)
                pdf.ln(5)
                for date, row in summary.iterrows():
                    line = f"{date} - Lunch: {row.get('Lunch', 0)} | Dinner: {row.get('Dinner', 0)} | Total: {row['Total Meals']}"
                    pdf.cell(200, 10, txt=line, ln=True)
                pdf_output = BytesIO()
                pdf.output(pdf_output)
                st.download_button("📄 Download Personal Report (PDF)", pdf_output.getvalue(), "personal_report.pdf", mime="application/pdf")

            else:
                st.warning("No data found for this Employee ID.")

        st.subheader("📊 Monthly Summary Report")
        monthly = meal_df.groupby(["Employee ID", "Join Date", "Section", "Meal"]).size().unstack(fill_value=0)
        monthly["Total"] = monthly.sum(axis=1)
        monthly["Average Meals/Day"] = (monthly["Total"] / pd.to_datetime(meal_df["Date"]).nunique()).round(2)

        st.dataframe(monthly)

        csv_all = monthly.to_csv().encode("utf-8")
        st.download_button("📥 Download Monthly Report (CSV)", csv_all, "monthly_report.csv", "text/csv")
