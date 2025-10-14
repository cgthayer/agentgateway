# Coding Guidelines

## All Languages

### Core Principles

- **Modularity & Feature Separation**:
   - Break out common functionality that's being used in 3 or more places to utility files and libraries.
   - If nesting becomes 4 or more levels deep it's probably best to move to it's own function.
   - If a file becomes close to 1000 lines, it's probably time to break it into several files.
   - **Features, concerns, and pluggable components should be separated into their own files and classes**
   - Each feature should be self-contained with its own API endpoints, services, and UI components
   - Avoid adding large new features to existing files - create dedicated modules instead
   - Before writing UI code, confirm assumptions about layout and style with users
- **Separation of Concerns (SOLID Principles)**:
   - **Single Responsibility**: Each module, class, or function should have one clear purpose or area of concern.
   - **Controlled Access**: Features should expose well-defined interfaces; internal implementation details should be private
   - **Interface Segregation**: Clients should not depend on interfaces they don't use; create focused, minimal interfaces
   - **Dependency Inversion**: Depend on abstractions (interfaces/protocols) rather than concrete implementations
   - **Database Modularity**: Database operations for feature-specific tables must only be accessed through that feature's service module. For example, the messaging module (MessageService) should be the sole access point to Message and Conversation models. Never bypass feature modules with direct database operations from other features. This maintains clear boundaries, makes refactoring safer, enables easier testing with mocks, and prevents tight coupling between unrelated features.
- Directories: major components should be separated such as directories for backend and frontend
- Structure: backend and frontend should communicate with a RESTful swagger API
- Comments: explain the intent of the code, but aren't needed to explain what the code does or how the code works
- Result checks: Always check for empty lists and error responses; inform humans when appropriate, and log with enough detail to debug.
- API consistency: Use the same Pydantic response model across all endpoints that return the same logical data type. Different response schemas for the same data cause frontend integration bugs.
- Network: 
    - all network calls never retry more than 3 times, and use exponential backoff with randomness. The user should only be notified on the first occurance to avoid flooding them with notifications. If we have given up, the user should be given a pop-up that let's them retry to start the process over.
    - calls are retried for temporary errors. calls aren't retried if they are for errors that are likely to re-occur like bad authentication.
- System calls: any system calls are checked for error results
- Datetime: the database may loose timezone data, so always store in UTC and assume retrieved datetimes are UTC. Or use unix epoch time.
- Lint: after making changes run lint checks when possible on the affected files. Always fix linting issues before considering a feature complete.
- Nulls: be careful to never dereference nulls.
- If there are multiple components (such as a frontend and backend) read @workbench.md for additional guidelines.
- Use types for variables when reasonable and possible.
- When adding new code, be sure to include dependencies if needed.
- Don't sleep if periodic checking is possible. It's better to move forward when something is ready, otherwise you're waiting unnecessarily.

### Other Guidelines

- In languages that implicitly return a value, like bash functions, return explicitly such as `return 0`.
- When making code updates, it's helpful to make a minor update to an info log line, so that it's easy to tell if we are
  accidentally looking at cached results.


## Development Methodology

Follow Kent Beck's approach: **Make it work, make it right, make it fast**

1. **Make it work**: Get the basic case working and tested
   - Focus on core functionality first
   - Write minimal code to satisfy requirements
   - Add basic tests to verify functionality

2. **Make it right**: Catch corner cases and apply best practices
   - Add comprehensive tests for edge cases
   - Apply coding standards from this document
   - For Python: reference `python-best-practices.md` for medium to large changes
   - Run linting and fix all issues before considering feature complete

3. **Make it fast**: Consider performance implications
   - Identify potential performance bottlenecks
   - Warn about choices that may impact performance
   - Suggest benchmark tests when performance is critical
   - Only optimize after measuring actual performance issues

### Development Approach

- When new functionality is added, make sure there's a short fast test for the basic cases
- When a problem is fixed, make sure there's a test that fails before the fix, and passes after the fix
- When possible, validate that code coverage is good for the stage of development. You may need to ask the user if we are in "make it work, right, or fast" mode
- **CRITICAL: Never tell the developer that something is working unless you have high confidence in it, which usually means a unittest was run**
- **When modifying tests**: ALWAYS run the tests immediately after making changes, before claiming they work or are fixed
- **When creating new tests**: Run them to verify they pass before adding to workbench or claiming completion
- **When fixing code based on test failures**: Run the tests again to verify the fix works
- **Changelog Updates**: Once a new file or change has been fully tested and verified working, update the CHANGELOG.md file to document the change in the [Unreleased] section following Keep a Changelog format

### Debugging

- Be certain you understand and validate the problem before changing code. Don't assume that you understand the problem without proof. The logs should make it clear where problems are happening in the call chain. Add logging as needed.
- When changing names, it's helpful to `grep` or `git grep` for the old term to be sure you've changed all references.
- If you are repeating the same steps, you may be in a loop. Think more deeply, enumerate your assumptions, and validate your assumptions quickly.

#### Validating Assumptions Quickly
- **Check model definitions before using fields**: Read the model file to verify attribute names exist
- **Use database introspection**: `dir(instance)` and `hasattr(instance, 'field')` to validate at runtime
- **Query ground truth directly**: Direct database queries bypass all caching layers
- **Verify code is actually running**: Check file contents in container match source

#### Async Operations
- **Log entry/exit points**: Async tasks fail silently without comprehensive logging
- **Use unique version markers**: `[COMPONENT-v2]` in log messages to distinguish new code from cached logs
- **Log parsed input data**: Verify correctness before processing
- **Always use `exc_info=True`**: Get full stack traces in error logging

#### Database Debugging
- **Query latest records explicitly**: `ORDER BY id DESC LIMIT 1` or by timestamp
- **Don't filter by content when debugging**: Content filters can match old/stale data
- **Direct queries are ground truth**: Bypass application caching, logs, and test scripts


### Testing

- When a problem is fixed, make sure there's a test that fails before the fix, and passes after the fix
- When new functionality is added, make sure there's a short fast test for the basic cases
- Validate that code coverage is good for the stage of development
- **Test scripts can show stale data**: Always verify critical results with independent database queries
- **Add timestamps to test output**: Makes it easy to identify when results are from old runs

### Binary Search Debugging

For complex systems with multiple components, use binary search debugging to efficiently isolate issues:

1. **Map the dependency chain**: From the failure point, identify all components in the call chain that could cause the failure (typically 4-6 candidates)
   - Example: Frontend error → API client → Backend endpoint → Database query → Data serialization → Response parsing

2. **Pick the middle candidate**: Test the component roughly halfway through the chain
   - For 6 candidates, test candidate #3
   - Use minimal changes: add logging, create a small test, or use manual verification

3. **Determine which half contains the issue**: Based on test results, eliminate half the candidates
   - If middle candidate works: issue is in the later half of the chain
   - If middle candidate fails: issue is in the earlier half of the chain

4. **Repeat until isolated**: Continue halving the search space until you pinpoint the exact failure point
   - This gives O(log n) debugging time vs O(n) linear debugging

**Testing Methods for Binary Search:**
- **Logging changes**: Add timestamped debug logs to verify data flow
- **Unit tests**: Create focused tests for specific components
- **Manual verification**: For UI components, use automated testing when possible, otherwise ask for human testing
- **API testing**: Use curl or API clients to test endpoints directly
- **Database queries**: Run direct SQL queries to verify data integrity

**Benefits:**
- Prevents wasted time debugging wrong assumptions
- Especially effective for multi-tier architectures (Frontend ↔ API ↔ Database)
- Scales logarithmically instead of linearly with system complexity
- Forces systematic thinking about component dependencies


## Javascript and Typescript Code Guidelines

UI and UX guidelines:
- use next.js and tailwind css for the UI
- separate client and server functionality clearly when appropriate
- make utility files when code is getting reused multiple times
- separate reusable structures into components when appropriate
- include light and dark UI modes
- separate and structure css so that updating themes is easy
- Use toast notifications. Color errors with red, warnings with yellow, information with blue, and success with green. Make the notification clear for the human with enough detail to debug AND log enough details in the console to pinpoint the issue.
- Major sections, divs, panes should be named (possibly using id)
- When providing a set of options, if appropriate highlight the primary call to action, which is the default choice.

All network calls to APIs should
- check for errors before trying to parse json results
- the error displayed to the user is clear, detailed, and unique enough to find where exactly in the code it came from
- the error messages logged to the console provide enough context for debugging

Error Handling Requirements:
- **User-facing errors**: Always display human-readable messages that are clear and concise. Never display "[object Object]" or raw error objects to users.
- **Error message extraction**: Handle different error response formats (string, {detail}, {message}, {error}) gracefully
- **Fallback messages**: Provide meaningful fallback messages when error parsing fails
- **Logging**: Log detailed error information to console for debugging, including:
  - Timestamp
  - URL/endpoint that failed
  - HTTP status code
  - Full error details
  - User context (if available)
- **Validation**: Always validate that thrown errors have a proper message property before displaying to users
- **Network errors**: Provide helpful messages for connection issues (e.g., "Unable to connect to server. Please check your internet connection.")
- **Loading states**: Disable relevant UI elements during async operations to prevent multiple submissions

Null/Undefined Safety:
- **Always use optional chaining (?.) when accessing object properties** - this is the preferred method for null safety
- Use nullish coalescing (??) for default values when dealing with null/undefined
- Before calling array methods like .length, .map(), .filter(), ensure the variable is not null/undefined
- Initialize arrays and objects with proper default values, but still guard against runtime null assignments
- Use TypeScript's strict null checks when possible
- **Date/Timestamp handling**: Always validate timestamps/date strings before passing to Date constructor
  - Use optional chaining first: `object?.timestamp ? new Date(object.timestamp) : new Date()`
  - Provide fallback display values: `object?.timestamp ? new Date(object.timestamp).toLocaleString() : 'Unknown'`
  - Consider invalid date strings that may cause Date constructor to return Invalid Date
- Examples of safe patterns (in order of preference):
  - `object?.property?.method()` instead of `object.property.method()` (PREFERRED)
  - `array && array.length > 0` instead of `array.length > 0`
  - `value ?? defaultValue` instead of `value || defaultValue`
  - `object?.timestamp ? new Date(object.timestamp).toLocaleString() : 'Unknown'` instead of `new Date(object.timestamp).toLocaleString()`

General guidelines:
- use typescript and typing where appropriate.
- have commonly used types in a separate file (types.ts).
- use ESLint 9+ with TypeScript support for linting.
- use Prettier for consistent code formatting.
- configure ESLint and Prettier to work together (use eslint-config-prettier).
- prefer `const` over `let` when variables won't be reassigned.
- use strict TypeScript configuration with noImplicitAny, strictNullChecks.
- organize imports: external libraries first, then internal modules.
- use meaningful variable and function names that describe their purpose.


## Python

### File Organization

Python files should follow this structure with sections separated by **two blank lines**:

1. **Module docstring** (if present)
2. **Imports** (always at top unless special circumstances)
   - Builtin modules
   - Third-party modules  
   - Local modules
   - Each section separated by one blank line, alpha-sorted within sections
3. **Global variables and constants**
4. **Classes**
5. **Functions and code**

**File Focus:**
- Each file should focus on a single purpose or area
- Small utility functions should go in `utils.py` or a separate utility collection
- Avoid mixing unrelated functionality in the same file


### General Guidelines

- **imports ALWAYS go to the top of the file** - NEVER use inline imports inside functions or methods (except in very rare cases like avoiding circular dependencies)
- imports are alpha sorted within their sections
- imports are in sections separate by a blank line: builtin modules, 3rd party modules, local modules
- when calling a function that has arguments with default values, use the full argument name in the call, except for dict.get()
- use ruff for linting, formatting, and import sorting (replaces black, flake8, isort)
- run `ruff check --fix` to auto-fix most issues
- run `ruff format` for code formatting
- avoid `== False` comparisons, use `not variable` instead
- use type hints where appropriate for better code clarity
- prefer f-strings over .format() or % formatting for string interpolation
- for medium to large changes, reference `python-best-practices.md` for detailed guidelines
- use ruff issue count as a "badness score" - aim for 0 issues before completion
- use types for arguments and results when reasonable. Prefer "Optional[type]" to "type | None"

### API Schema and Database Model Architecture

**Layer Separation:**
- **Pydantic schemas** (`app/schemas/`): Define API contracts, validation, and serialization
- **SQLAlchemy models** (`app/models/`): Define database schema, constraints, and relationships
- **Service layer** (`app/services/`): Bridge between API and database with business logic

**Pydantic Schema Guidelines:**
- Use `Annotated[Type, Field(...)]` for field constraints and documentation
- Follow Postel's Law: Be lenient in what you accept (nullable inputs), specific in what you emit (non-null outputs)
- Use `@field_validator` with `mode='before'` to convert database nulls to API defaults
- Validate format and structure, not business rules (uniqueness, existence)
- **Foreign Key Field Handling**: Keep nullable foreign keys as `Optional[int] = None` in API schemas to avoid constraint violations
- Example:
  ```python
  username: Annotated[str, Field(min_length=1, max_length=50)]
  full_name: Annotated[Optional[str], Field(default="")] = ""  # Nullable in DB, "" in API
  module_id: Optional[int] = None  # Nullable foreign key - keep as None, don't convert to 0
  
  @field_validator('full_name', mode='before')
  @classmethod
  def convert_none_to_empty_string(cls, v):
      return "" if v is None else v
  ```

**SQLAlchemy Model Guidelines:**
- Use explicit `nullable=False` for required fields (columns are nullable by default)
- Use `server_default=func.now()` for timestamp fields with UTC timezone
- Use `unique=True` and `index=True` for fields requiring uniqueness and fast lookups
- Store timestamps as `DateTime(timezone=True)` to preserve UTC timezone information
- **Foreign Key Nullability**: Keep foreign key columns nullable when the relationship is optional (e.g., `module_id` when modules may not be assigned)
- Example:
  ```python
  username = Column(String, unique=True, index=True, nullable=False)
  created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  full_name = Column(String, nullable=True)  # Can be null in database
  module_id = Column(Integer, ForeignKey('modules.id'), nullable=True)  # Optional relationship
  ```

**Service Layer Guidelines:**
- Handle database constraint violations (IntegrityError) and convert to user-friendly errors
- Perform business logic validation (uniqueness checks, authorization)
- Bridge between Pydantic validation and SQLAlchemy persistence

**Foreign Key Best Practice:**
When a foreign key relationship is optional (nullable in database), follow this pattern:
1. **Database**: Keep the foreign key column nullable (`nullable=True`)
2. **API Schema**: Keep the field as `Optional[int] = None` - do NOT convert NULL to 0 or other default values
3. **Validation**: Only convert NULL to defaults for non-foreign-key fields (strings, booleans, etc.)

**Why**: Converting NULL foreign keys to default values (like 0) can violate foreign key constraints if that default value doesn't exist in the referenced table. This causes 500 Internal Server Errors during API response serialization.

Database Query Safety:
- **NEVER use .first() without validation** - always check that exactly one result is expected
- Instead of .first(), always run the query and generate a warning or error if >1 results are returned.
- Use .one() when exactly one result is required (raises exception if 0 or >1 results) and only if a unique constraint exists on the field.
- Use .one_or_none() when 0 or 1 result is expected (raises exception if >1 results)
- Use .first() only when you explicitly want the first result from multiple potential results, and the query must have a sort order.
- **Always call .unique() before .one() or .one_or_none()** when the query includes joined eager loads against collections (relationships). This prevents "The unique() method must be invoked" errors.

**Smolagents Tool Development:**
When creating tools that inherit from `smolagents.Tool`, follow these requirements:
- **Required attributes**: `name`, `description`, `inputs`, `output_type`, and `forward()` method
- **Optional parameters**: All optional parameters (with default values) MUST have `"nullable": True` in their input definition
- **Parameter types**: Use "string", "boolean", "integer", "number" as type values
- **Field name validation**: ALWAYS check the actual model definition before accessing fields. Use `grep` or read the model file to verify field names exist.
- **Testing requirements**:
  - Create unit tests that use `Mock(spec=ModelClass)` to validate field access
  - Tests MUST set actual field names from the model (not arbitrary names)
  - Tests MUST call the tool's `forward()` method with realistic data to catch AttributeError
  - Add test that specifically validates field names match the model definition
- **Workbench integration**: Add new tool tests to the `workbench` test suite so they run with `./workbench test`

**Prevention of Field Name Mismatches:**
Before writing code that accesses model fields:
1. **Read the model file** to see actual field names: `grep "class ModelName" -A 30 app/models/*.py`
2. **Never assume field names** based on patterns or conventions
3. **Write tests with real field names** using `Mock(spec=ModelClass)` to catch typos
4. **Run tests before committing** - field access errors will raise AttributeError

Also see [python-best-practices.md](python-best-practices.md) for more details.


## Command-Line Tools

- **curl with jq**: Always use `-s` flag to prevent progress bar from breaking JSON parsing: `curl -s http://localhost:8000/api/endpoint | jq .`
- **psql pager**: When using `psql` in scripts or automated contexts, disable the pager to prevent interactive prompts:
  - Use `PAGER=cat` environment variable: `PAGER=cat psql -U user -d database -c "SELECT ..."`
  - Or use `--pset=pager=off` flag: `psql --pset=pager=off -U user -d database -c "SELECT ..."`
  - Or pipe through `cat`: `psql -U user -d database -c "SELECT ..." | cat`
  - This prevents psql from waiting for user input when output exceeds terminal height


## Docker

- Be careful of the argument order. For example "docker-compose logs frontend --tail=50" will fail, but "docker-compose logs --tail=50 frontend" will work.
- For volume mount conflicts and debugging container startup issues, see [docker-debugging.md](docker-debugging.md)


## About

This document should be reviewed monthly to ensure best practices remain current based on industry standards and tool updates. Before conducting this analysis, ask for permission as it can be a distraction from active development work.
