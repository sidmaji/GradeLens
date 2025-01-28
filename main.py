import requests
import streamlit as st

# Set up the page configuration
st.set_page_config(
    page_title="Student GPA Tracker",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={
        "Get help": "mailto:siddhant.maji@gmail.com",
        "Report a Bug": None,
        "About": "Created by Siddhant Maji, this app helps students track their GPA and grades easily with data from Frisco ISD's Home Access Center.",
    },
)


# Helper function to calculate GPA
def calculate_weighted_gpa(class_names, class_grades):
    try:
        total_weighted_grade = 0
        max_weighted_grade = 0
        classes_num = len(class_names)

        for i in range(classes_num):
            if not class_grades[i]:
                classes_num -= 1
                i += 1
            else:
                grade = int(round(float(class_grades[i])))
                class_name = class_names[i]
                if (
                    "AP" in class_name
                    or "IB" in class_name
                    or "Computer Sci 3 Adv" in class_name
                ):
                    total_weighted_grade += max(0, 6.0 - ((100 - grade) / 10))
                    max_weighted_grade += 6.0
                elif "Adv" in class_name:
                    total_weighted_grade += max(0, 5.5 - ((100 - grade) / 10))
                    max_weighted_grade += 5.5
                else:
                    total_weighted_grade += max(0, 5.0 - ((100 - grade) / 10))
                    max_weighted_grade += 5.0

        weighted_gpa = round(total_weighted_grade / classes_num, 4)
        max_weighted_gpa = round(max_weighted_grade / classes_num, 4)
        return weighted_gpa, max_weighted_gpa
    except Exception as e:
        print(e)
        return 0.000, 0.000


# Fetch student data from APIs
def fetch_student_info(username, password):
    api_url = "https://friscoisdhacapi.vercel.app/api/info"
    payload = {"username": username, "password": password}
    response = requests.get(api_url, params=payload)
    return response.json()


def fetch_schedule(username, password):
    api_url = "https://friscoisdhacapi.vercel.app/api/schedule"
    payload = {"username": username, "password": password}
    response = requests.get(api_url, params=payload)
    return response.json()


def fetch_student_classes(username, password):
    api_url = "https://friscoisdhacapi.vercel.app/api/currentclasses"
    payload = {"username": username, "password": password}
    response = requests.get(api_url, params=payload)
    return response.json()


# Streamlit App
# st.title("Student GPA Tracker")

# Sidebar Navigation
page = st.sidebar.selectbox(
    "Select a page",
    [
        "Login",
        "GPA & Class Information",
        "Schedule",
        "About",
        "Other Features",
    ],  # Add more pages as you expand
)

if page == "Login":
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            student_info = fetch_student_info(username, password)
            if "name" in student_info:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.password = password
                st.session_state.student_info = student_info
                st.success(f"Welcome, {student_info['name']}!")
            else:
                st.error("Invalid credentials. Please try again.")
    else:
        st.success("Already logged in!")

elif page == "GPA & Class Information":
    st.title("GPA & Class Information")
    if st.session_state.authenticated:
        st.markdown("---")
        with st.spinner(text="Fetching data..."):
            st.header("Student Information")
            student_info = st.session_state.student_info
            st.write(f"**Name:** {student_info['name']}")
            st.write(f"**Campus:** {student_info['campus']}")
            st.write(f"**Grade Level:** {student_info['grade']}")

            st.header("Class Information")
            student_classes = fetch_student_classes(
                st.session_state.username, st.session_state.password
            )
            class_names = []
            class_grades = []
            class_assignments = []

            if "currentClasses" in student_classes:
                for c in student_classes["currentClasses"]:
                    class_names.append(c["name"])
                    class_grades.append(c["grade"])
                    class_assignments.append(c["assignments"])

                for i in range(len(class_names)):
                    class_name = class_names[i]
                    class_grade = class_grades[i]
                    class_assignments_data = class_assignments[i]

                    st.subheader(" ".join(class_name.split(" ")[3:]))
                    st.write(f"**Grade:** {class_grade}")

                    # Create an expander for assignments
                    with st.expander("Assignments"):
                        if class_assignments_data:
                            for assignment in class_assignments_data:
                                st.write(
                                    f"- **{assignment['name']}**: {assignment['score']}/{assignment['totalPoints']}"
                                )
                        else:
                            st.write("No assignments available")

            weighted_gpa, max_gpa = calculate_weighted_gpa(class_names, class_grades)
            st.header("GPA")
            st.metric("Weighted GPA", f"{weighted_gpa:.4f}")
            st.metric("Max Weighted GPA", f"{max_gpa:.4f}")

            if st.button("Logout"):
                st.session_state.clear()
                st.success("You have been logged out.")
    else:
        st.error("Please log in first.")

elif page == "Schedule":
    st.title("Student Schedule")
    if st.session_state.authenticated:
        # Fetch data from the API
        schedule_data = fetch_schedule(
            st.session_state.username, st.session_state.password
        )

        if schedule_data and "studentSchedule" in schedule_data:
            student_schedule = schedule_data["studentSchedule"]

            # Display the schedule
            for course in student_schedule:
                with st.expander(course.get("courseName", "Unknown Course")):
                    # Display the selected fields with defaults
                    st.write(f"**Course Name:** {course.get('courseName', 'N/A')}")
                    st.write(f"**Teacher:** {course.get('teacher', 'N/A')}")
                    st.write(f"**Room:** {course.get('room', 'N/A')}")
                    st.write(
                        f"**Marking Periods:** {course.get('markingPeriods', 'N/A')}"
                    )
                    st.write(f"**Periods:** {course.get('periods', 'N/A')}")
                    st.write(f"**Days:** {course.get('days', 'N/A')}")
        else:
            st.error("No schedule data available or failed to fetch data.")
    else:
        st.error("Please log in first.")
elif page == "About":
    if st.session_state.authenticated:
        st.title("About This Application")

        st.write(
            """
            **GradeLens** serves as your complete academic management system which helps students effectively organize their academic activities and track school life effectively.
            **Features:**
            - **Student Schedule**: View your class schedule with real-time data fetched from the Frisco ISD API. 
            This includes details like course names, room assignments, teacher information, marking periods, and class days.
            - **GPA Calculator**: Calculate your GPA by entering grades, course levels (on-level, advanced, AP), and using the appropriate weights for each class. 
            This tool also allows you to separate first and second semesters and track your progress throughout the year.
            - **Class Information**: Get detailed information about your classes, including course codes and names, so you can stay on top of assignments and class expectations.

            **How It Works:**
            - Simply log in with your Frisco ISD credentials to fetch your schedule data and start using the tools provided.
            - The GPA Calculator helps you calculate your GPA based on specific formulas and course weights.
            - Easily navigate between your schedule, GPA, and class information all in one place.

            **Disclaimer:**
            The information provided in this application is based on the data available through the Frisco ISD API. 
            Schedule, GPA, and class information may change. The app is intended for informational purposes to help students stay organized.

            **Credits:**
            - Developed by: Siddhant Maji
            """
        )
    else:
        st.error("Please log in first.")
elif page == "Other Features":
    # Add functionality for future pages, like reports, settings, etc.
    st.header("Coming Soon!")
    st.write("More features will be added here later.")
