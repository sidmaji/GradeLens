import os
import requests
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from bs4 import BeautifulSoup
import lxml

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configuration
HAC_BASE_URL = "https://hac.friscoisd.org"

# Models
class ClassData(BaseModel):
    name: str
    grade: float | None
    assignments: list[dict]

# Helper Functions
def getRequestSession(username: str, password: str) -> requests.Session:
    requestSession = requests.Session()

    # Fetch the login page to get the verification token
    loginScreenResponse = requestSession.get(
        f"{HAC_BASE_URL}/HomeAccess/Account/LogOn?ReturnUrl=%2fHomeAccess%2f"
    ).text

    parser = BeautifulSoup(loginScreenResponse, "lxml")
    requestVerificationToken = parser.find(
        "input", attrs={"name": "__RequestVerificationToken"}
    )["value"]

    # Prepare headers and payload for login
    requestHeaders = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Host": "hac.friscoisd.org",
        "Origin": "hac.friscoisd.org",
        "Referer": "https://hac.friscoisd.org/HomeAccess/Account/LogOn?ReturnUrl=%2fhomeaccess%2f",
        "__RequestVerificationToken": requestVerificationToken,
    }

    requestPayload = {
        "__RequestVerificationToken": requestVerificationToken,
        "SCKTY00328510CustomEnabled": "False",
        "SCKTY00436568CustomEnabled": "False",
        "Database": "10",
        "VerificationOption": "UsernamePassword",
        "LogOnDetails.UserName": username,
        "tempUN": "",
        "tempPW": "",
        "LogOnDetails.Password": password,
    }

    # Perform login
    requestSession.post(
        f"{HAC_BASE_URL}/HomeAccess/Account/LogOn?ReturnUrl=%2fHomeAccess%2f",
        data=requestPayload,
        headers=requestHeaders,
    )

    return requestSession

def get_student_data(username: str, password: str) -> dict:
    session = getRequestSession(username, password)

    # Fetch registration page for student info
    registration_page_content = session.get(
        f"{HAC_BASE_URL}/HomeAccess/Content/Student/Registration.aspx"
    ).text

    registration_parser = BeautifulSoup(registration_page_content, "lxml")

    student_info = {
        "id": None,
        "name": registration_parser.find(id="plnMain_lblRegStudentName").text,
        "birthdate": registration_parser.find(id="plnMain_lblBirthDate").text,
        "campus": registration_parser.find(id="plnMain_lblBuildingName").text,
        "grade": registration_parser.find(id="plnMain_lblGrade").text,
        "counselor": registration_parser.find(id="plnMain_lblCounselor").text,
        "totalCredits": "0",
    }

    # Try to get the student ID, fallback to schedule page if necessary
    try:
        student_info["id"] = registration_parser.find(id="plnMain_lblRegStudentID").text
    except AttributeError:
        schedule_page_content = session.get(
            f"{HAC_BASE_URL}/HomeAccess/Content/Student/Classes.aspx"
        ).text
        schedule_parser = BeautifulSoup(schedule_page_content, "lxml")
        student_info["id"] = schedule_parser.find(id="plnMain_lblRegStudentID").text

    # Fetch assignments page for current classes
    assignments_page_content = session.get(
        f"{HAC_BASE_URL}/HomeAccess/Content/Student/Assignments.aspx"
    ).text

    assignments_parser = BeautifulSoup(assignments_page_content, "lxml")
    current_classes = []
    course_containers = assignments_parser.find_all("div", "AssignmentClass")

    for container in course_containers:
        new_course = {"name": "", "grade": "", "lastUpdated": "", "assignments": []}

        course_parser = BeautifulSoup(f"<html><body>{container}</body></html>", "lxml")
        header_container = course_parser.find_all("div", "sg-header sg-header-square")
        assignments_container = course_parser.find_all("div", "sg-content-grid")

        for hc in header_container:
            header_parser = BeautifulSoup(f"<html><body>{hc}</body></html>", "lxml")
            new_course["name"] = header_parser.find(
                "a", "sg-header-heading"
            ).text.strip()
            new_course["lastUpdated"] = (
                header_parser.find("span", "sg-header-sub-heading")
                .text.strip()
                .replace("(Last Updated: ", "")
                .replace(")", "")
            )
            new_course["grade"] = (
                header_parser.find("span", "sg-header-heading sg-right")
                .text.strip()
                .replace("Student Grades ", "")
                .replace("%", "")
            )

        for ac in assignments_container:
            assignments_parser = BeautifulSoup(
                f"<html><body>{ac}</body></html>", "lxml"
            )
            rows = assignments_parser.find_all("tr", "sg-asp-table-data-row")

            for assignment_container in rows:
                try:
                    assignment_parser = BeautifulSoup(
                        f"<html><body>{assignment_container}</body></html>", "lxml"
                    )
                    tds = assignment_parser.find_all("td")

                    assignment_name = assignment_parser.find("a").text.strip()
                    assignment_date_due = tds[0].text.strip()
                    assignment_date_assigned = tds[1].text.strip()
                    assignment_category = tds[3].text.strip()
                    assignment_score = tds[4].text.strip()
                    assignment_total_points = tds[5].text.strip()

                    new_course["assignments"].append(
                        {
                            "name": assignment_name,
                            "category": assignment_category,
                            "dateAssigned": assignment_date_assigned,
                            "dateDue": assignment_date_due,
                            "score": assignment_score,
                            "totalPoints": assignment_total_points,
                        }
                    )
                except Exception:
                    pass

        current_classes.append(new_course)

    # Fetch schedule page for student schedule
    schedule_page_content = session.get(
        f"{HAC_BASE_URL}/HomeAccess/Content/Student/Classes.aspx"
    ).text

    schedule_parser = BeautifulSoup(schedule_page_content, "lxml")
    schedule = []

    courses = schedule_parser.find_all("tr", "sg-asp-table-data-row")

    for row in courses:
        row_parser = BeautifulSoup(f"<html><body>{row}</body></html>", "lxml")
        tds = [x.text.strip() for x in row_parser.find_all("td")]

        if len(tds) > 3:
            schedule.append(
                {
                    "building": tds[7],
                    "courseCode": tds[0],
                    "courseName": tds[1],
                    "days": tds[5],
                    "markingPeriods": tds[6],
                    "periods": tds[2],
                    "room": tds[4],
                    "status": tds[8],
                    "teacher": tds[3],
                }
            )

    return {
        "studentInfo": student_info,
        "currentClasses": current_classes,
        "studentSchedule": schedule,
    }

def calculate_weighted_gpa(
    class_names: list[str], class_grades: list[float | None]
) -> tuple[float, float]:
    total_weighted_grade = 0.0
    max_weighted_grade = 0.0
    valid_classes = 0

    for class_name, grade in zip(class_names, class_grades):
        if grade is None:
            continue

        valid_classes += 1
        grade = round(grade)

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

    if valid_classes == 0:
        return 0.0, 0.0

    weighted_gpa = round(total_weighted_grade / valid_classes, 4)
    max_weighted_gpa = round(max_weighted_grade / valid_classes, 4)
    return weighted_gpa, max_weighted_gpa

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "base.html", {"request": request, "content": "login.html"}
    )

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        # Fetch all student data (info, current classes, and schedule)
        student_data = get_student_data(username, password)

    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid credentials or API error.")

    class_data = [
        {
            "class_name": " ".join(c["name"].split(" ")[3:]),
            "class_grade": float(c["grade"]) if c["grade"] else None,
            "assignments": c["assignments"],
        }
        for c in student_data.get("currentClasses", [])
    ]

    weighted_gpa, max_gpa = calculate_weighted_gpa(
        [c["class_name"] for c in class_data],
        [c["class_grade"] for c in class_data],
    )

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "content": "dashboard.html",
            "name": username,
            "gpa": weighted_gpa,
            "max_gpa": max_gpa,
            "classes": class_data,
            "studentInfo": student_data.get("studentInfo", {}),  # Pass student info
            "schedule": student_data.get("studentSchedule", []),  # Pass schedule data
        },
    )