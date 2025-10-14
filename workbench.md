
# Workbench

The idea of the Workbench is that a software application or system can be brought up, tested, and debugged with a single laptop, and if possible without Internet access. This makes it possible for all the developers to make progress and iterate quickly without needing to rely on other development servers running, which might be unstable.

The key elements of the Workbench Concept are:
* Complete: The entire application, including all it programs, can be brought up on a single computer.
* Isolated: The application can be run without access to the Internet, or as few outside dependencies as absolutely required.
* Debuggable: It's run in a way that artifacts are kept in one place for easy inspection, and observability is supported (such as metrics, logs, and traces).

## Guidelines
* As many of the required components as possible can be run locally.
* It's fast to bring up and take down the full application so that iteration can happen quickly. This typically means it should start in less than 30 secs once requirements are cached.
* The code can be changed while most of the system is up, though editing a file may require restarting the components that use it. In the development environment's docker-compose.yml, source code may be a shared volume with the host, for quick iteration. In production that should be `COPY . .` since the source won't be mounted there. More details, if needed, in [docker-debugging.md][docker-debugging.md]
* The application creates any artifacts in a `workbench_data` folder so that they can be used for debugging and examination.
* The entire system can be tested for the "Happy Path" very quickly. This typically means in less than 30 secs once the system is running.
* The entire system can be tested fully running end-to-end tests that exercise the interaction between all components.
* The workbench has a simple "smoketest" that brings it up, does a minimal test that the software can run without crashing, and brings everything down. This can be run in the CI/CD environment for all code commits. If the workbench is already running, it doesn't stop it when it completes.
* Service startup uses active polling instead of fixed delays - checks service health every 3 seconds with configurable timeout (default 30s), returning immediately when services are ready rather than waiting for arbitrary sleep durations.
* When it makes sense, external data is cached for reproducibility and testing.
* Versions of dependencies are tracked, pinned, and recorded in version control.

## Suggestions
* Ideally, making changes restarts the necessary components automatically.
* For consistency, the repository supports a shell script this `workbench (start | stop | test | e2e | smoketest)`.
* For substantial projects, workbench may support `workbench start [component]` such as `workbench start frontend` and `workbench test database`
  in order to speed up the development process.
* Workbench may support `workbench restart` which is exactly the same as `workbench stop && workbench start`.
* Workbench may support `workbench status` which let's you know if the workbench is running, and if so, what components are running.
* If there are possible structure changes, such are database migrations or data generation, it may help to have a `workbench (init | update)`. If possible these can be run automatically when necessary by `workbench start`. E.g. if there are new migrations it should run them.

## Code Changes

When making code changes it's may help to update the workbench.

- When adding new tests, make sure the tests are run from one of the workbench testing commands (e.g. `workbench test` or `workbench e2e`).
- After any code change, there is probably a workbench test to run that helps verify it's working. If not we may need to add one.

