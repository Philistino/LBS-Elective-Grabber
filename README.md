# LBS-Elective-Grabber
Digital Investing, Leading Teams and Organizations, Paths to Power, Negotiation and Bargaining, Distressed Investing...

Want the ultimate electives schedule?
Sick of wasting countless hours fighting for the schedule your want? 

Run this script to refresh the Enrolment Management System webpage and automatically add courses from your shortlist.

# To get started
This was tested with python 3.9, but it should work with python 3.6+. Pick your flavour of chromedriver and set that up however you want.
- pip install -r requirements.txt
- Rename "example_config.toml" -> "config.toml" and update with your details.
- For ultimate uptime, I recommend running on an always-on linux box, such as a cloud compute instance (oracle free tier is fine), with chrome driver in a docker container.
  - For a simpler approach, one can run this script on their laptop/desktop with Chrome and chromedriver (https://chromedriver.chromium.org/downloads).
- On linux (and maybe macOS), use nohup to prevent script from stopping when logging out. For example:
  - nohup python3.9 lbs_elective_grabber.py

# Notes
- Don't be a jerk and get in the way of other students' trades. Everyone struggles to get the courses they want.
  - The page refresh interval has a lower bound of mitigate trade intercepts.
- Logging in requires 2FA so you need your phone when starting the script.
- The website undergoes maintenance frequently so the script may timeout in the wee hours when EMS is down.
  - If the page does not load as normal, the script will retry three times with a 5-minute delay.
- If you run out of credits, you will not be able to add more courses.
- You cannot enroll in more than one section of a course. Try trading your section to a classmate or drop the unwanted section.
