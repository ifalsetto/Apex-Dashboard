# FalseTech Local Port Map

Use stable ports so stacks do not collide during local development.

| Stack | Service | Host port | Container port |
| --- | --- | ---: | ---: |
| Apex Dashboard | Streamlit dashboard | 8501 | 8501 |
| SimLay | Streamlit UI | 8502 | 8501 |
| SimLay | FastAPI API | 8000 | 8000 |
| Local AI | API | 8010 | 8000 |
| Automation workers | no public port by default | n/a | n/a |

Rules:

1. Publish only services that need host/browser access.
2. Internal services should communicate by Compose service name.
3. Workers should normally expose no host ports.
4. Databases should stay internal unless local debugging requires temporary exposure.
