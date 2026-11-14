# AI Response: Architecture design

- Date: 15 Nov 2026
- Tool: Claude
- Prompt file: ARCH-prompt-01.md

## Response

I'll check the project's existing design docs for consistency, then write the architecture page and render the PlantUML diagram.

Rendering the package diagram now (got a current PlantUML). Next I'll check the labels and write the wiki page.

Diagram is readable but the layers still stagger diagonally. I'll try one more layout tweak, then write the wiki page.

Wiki page is written and the dependency-rule test works on a toy app (it passes clean code and catches 3 kinds of bad import). Last step: a final look at the diagram and sending you the files.

I've written the architecture as a GitHub Wiki page, rendered the package diagram, and kept the PlantUML source. The wiki page has your six sections in order and covers all seven deliverables. I haven't run any of it against a real Django project.

**Chosen pattern:** Layered Architecture with three layers: Presentation, Application and Storage. MVC sits inside Presentation (templates are the View; `views.py`, `urls.py` and `forms.py` are the Controller). The OTP sender and the IUB Records client are behind small interfaces in the Storage layer, and `settings.py` picks which implementation to use.

**Dependency rule:** imports go downwards only. `views.py` never imports `models.py`, `delivery.py` or `records.py`. `constants.py` is the one shared file, and it imports nothing.

**Trade-off:** more files and pass-through code. Django shortcuts such as `ModelForm`, generic views and the admin skip the Application layer, so the page says not to use them for business actions.

**Dependency-rule test:** I added a small test (`tests/test_architecture.py`) that checks the rule. I ran it on a toy app, and it passed clean code and caught three kinds of bad import.

**Diagram:** it is grayscale only, with fill #F1F1F1, border #181818, a white background, no shadows and top-to-bottom direction, and every label is readable. The layers sit in a slight diagonal; I tried to straighten it and the alternatives put arrows through the layer titles. I rendered the PNG with Liberation Serif, a Times-metric font, because Times New Roman isn't installed here. The `.puml` still asks for Times New Roman.

**To publish the wiki page**, paste the Markdown into a new wiki page. Put the PNG at `images/fixit_package_diagram.png` in the wiki repository, or edit the image path.

## Assumptions
1. **Single app:** one Django app named `campus`, in a project package `fixit_campus`. If `services.py` passes about 300 lines, split it into a `services/` package.
2. **`records.py` is an addition:** you listed `delivery.py`, but the IUB Records client is not a delivery concern, so it gets its own file.
3. **Storage layer scope:** I put outside-system access in the Storage layer ("data and outside systems") so the layer count stays at three.
4. **Strict layering:** views use model objects returned by services but never import or query models.
5. **Login and OTP:** login uses university ID plus password, and OTP is used only for registration and password reset. IUB Records returns name, role, email and phone, and the OTP goes to the contact on record.
6. **Notifications:** they are in-app records. The message service is used only for OTPs, as in your brief. The SDS also mentions email or SMS to supervisors for safety hazards; that would be a second sender interface of the same kind.
7. **Overdue check:** it runs as a management command (`mark_overdue`) started by the operating system scheduler, and it calls one service function.
8. **Real implementations:** I did not design `HttpOtpSender` or the real records client. Development uses a console sender and a fake records client.
9. **Django admin:** it is not used for the Administrator role. Admin pages are the app's own views.
10. **Local files:** uploaded complaint photos go to a local `media/` folder.

Files are in /home/claude/work:
- FixIt_Campus_Architecture_Wiki.md
- fixit_package_diagram.png
- fixit_package_diagram.puml