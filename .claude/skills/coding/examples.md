# Coding rule BAD/GOOD examples

These selected examples clarify the rules in [SKILL.md](SKILL.md).
They are interpretation aids, not syntax or framework mandates. Repository
evidence and the canonical rule always take precedence.

## CodeGraph and Context Mode

### G1. Use CodeGraph for structural discovery

**BAD** — rebuild a call path through broad text search and repeated reads:

```bash
rg "RequestHandler" src
```

**GOOD** — in the main MCP-capable session, ask the graph for the relevant
source, relationships, and impact:

```text
codegraph_explore(query: "Where is RequestHandler invoked and what depends on it?")
```

A subagent or non-MCP session uses the CLI equivalent against the same
`.codegraph` index:

```bash
codegraph explore "Where is RequestHandler invoked and what depends on it?"
```

Use `rg` when the question is an exact string or configuration lookup rather
than a source relationship.

### G2. Select targeted tests from changed paths

Before choosing an authorised targeted test, include tracked and relevant
untracked source paths:

```bash
{
  git diff --name-only HEAD
  git ls-files --others --exclude-standard
} | codegraph affected --stdin --quiet
```

Treat the result as a candidate set. It does not override repository-required
checks or prove that omitted tests are unaffected.

### G3. Analyse a large file without loading it into the conversation

Context Mode's data-processing surface is MCP, so this is an MCP tool call, not
a shell command:

```text
ctx_execute_file(
  path: "access.log",
  language: "javascript",
  code: "const counts = {}; for (const line of FILE_CONTENT.split('\\n')) { const match = line.match(/^(\\S+).*\\s500\\s/); if (match) counts[match[1]] = (counts[match[1]] || 0) + 1; } console.log(JSON.stringify(counts));"
)
```

Only the computed IP counts enter context; the raw log remains in the sandbox.
Use native `Read` instead when exact bytes are needed for an edit.

### G4. Keep verbose targeted-test output outside the conversation

```text
ctx_execute(
  language: "shell",
  code: "./gradlew test --tests ExampleServiceTest",
  intent: "test summary failures exceptions"
)
```

Run only a test command already authorised by the task. Return the compact
matching evidence rather than the complete build log. Use `ctx_batch_execute`
instead only for three or more related commands, keeping `concurrency: 1` for
tests or other commands that share build state.

### G5. Contain a potentially large CodeGraph CLI result

When the MCP tool is unavailable and `codegraph explore` may be noisy, run the
CLI inside Context Mode rather than allowing its raw stdout into the session:

```text
ctx_execute(
  language: "shell",
  code: "codegraph explore 'Trace RequestHandler callers and dependents'",
  intent: "RequestHandler call path dependents source locations"
)
```

This combines the CLI fallback with Context Mode's MCP sandbox. It does not
replace the normal `codegraph_explore` MCP path.

## Simplicity

### S1. Implement only the stated requirement

**BAD** — a display-name requirement grows into an account-normalization system:

```python
def display_name(user, fallback="Anonymous", normalize_unicode=True):
    if user is None:
        return fallback
    return normalize(user.name) if normalize_unicode else user.name
```

**GOOD** — implement the requested behavior directly:

```python
def display_name(user):
    return user.name
```

### S2. Check existing solutions before adding code

**BAD** — write a parser before checking the repository, platform, or dependencies:

```python
def parse_timestamp(value):
    date, time = value.split("T")
    # custom parsing continues...
```

**GOOD** — after confirming no repository helper exists, use the standard library:

```python
from datetime import datetime

timestamp = datetime.fromisoformat(value)
```

The review should be able to name the evidence used to move through the YAGNI, existing-code, standard-library, installed-dependency, and new-code checks.

### S3. Require evidence for extra logic

**BAD** — defend against an imagined caller:

```python
def total(order):
    if order is None:  # A future caller might pass None.
        return 0
    return sum(item.price for item in order.items)
```

**GOOD** — follow the established non-null contract:

```python
def total(order):
    return sum(item.price for item in order.items)
```

### S4. Do not add unrequested guards, fallbacks, retries, or configuration

**BAD**:

```python
def load_user(user_id, retries=3, fallback=None):
    for attempt in range(retries):
        try:
            return repository.get(user_id)
        except TemporaryError:
            if attempt == retries - 1:
                return fallback
```

**GOOD**:

```python
def load_user(user_id):
    return repository.get(user_id)
```

### S5. Trust invariants guaranteed by construction

**BAD** — revalidate a collection the constructor already guarantees is non-empty:

```go
func First(batch NonEmptyBatch) Item {
    if len(batch.Items) == 0 {
        return Item{}
    }
    return batch.Items[0]
}
```

**GOOD**:

```go
func First(batch NonEmptyBatch) Item {
    return batch.Items[0]
}
```

### S6. Do not abstract one concrete implementation without approval

**BAD**:

```typescript
interface ClockStrategy {
  now(): Date;
}

class SystemClockStrategy implements ClockStrategy {
  now(): Date { return new Date(); }
}

const clock = new SystemClockStrategy();
```

**GOOD**:

```typescript
const now = new Date();
```

### S7. Prefer fewer concepts, branches, files, and lines

**BAD**:

```python
class NameFormatter:
    def format(self, name):
        return name.strip()

formatter = NameFormatter()
result = formatter.format(name)
```

**GOOD**:

```python
result = name.strip()
```

Delete the unnecessary layer when both versions satisfy the requirement.

## Locality and abstraction

### L1. Keep one-off logic at the call site

**BAD**:

```python
def is_eligible_age(age):
    return age >= 18

if is_eligible_age(user.age):
    enroll(user)
```

**GOOD**:

```python
if user.age >= 18:
    enroll(user)
```

### L2. Extract only for reuse or a material readability gain

**BAD** — a helper merely relocates one obvious expression:

```python
def calculate_line_total(quantity, price):
    return quantity * price

line_total = calculate_line_total(quantity, price)
```

**GOOD** — repeated, meaningful domain logic has one name:

```python
def taxable_subtotal(lines):
    return sum(line.quantity * line.price for line in lines if line.taxable)

domestic_tax_base = taxable_subtotal(domestic_lines)
export_tax_base = taxable_subtotal(export_lines)
```

### L3. Avoid theoretical extension points

**BAD**:

```java
interface UserReaderFactory {
    UserReader create(Configuration configuration);
}
```

**GOOD**:

```java
UserReader reader = new DatabaseUserReader(connection);
```

### L4. Prefer obvious duplication to a high-cost abstraction

**BAD** — two clear assignments become a generic field engine:

```javascript
applyFields(customer, source, [
  { target: "name", transform: trim },
  { target: "email", transform: lower },
]);
```

**GOOD**:

```javascript
customer.name = source.name.trim();
customer.email = source.email.toLowerCase();
```

## Code style

### C1. Use descriptive names

**BAD**:

```python
for x in xs:
    ttl += x.amt
```

**GOOD**:

```python
for invoice in invoices:
    total_amount += invoice.amount
```

### C2. Use intermediate variables when they aid debugging

**BAD**:

```python
return publish(serialize(validate(transform(load(path)))))
```

**GOOD**:

```python
record = load(path)
transformed_record = transform(record)
validated_record = validate(transformed_record)
payload = serialize(validated_record)
return publish(payload)
```

### C3. Prefer a traceable loop over a dense chain

**BAD**:

```javascript
const total = orders.filter(o => o.active).map(o => o.amount).reduce((a, b) => a + b, 0);
```

**GOOD**:

```javascript
let total = 0;
for (const order of orders) {
  if (order.active) {
    total += order.amount;
  }
}
```

### C4. Avoid clever reflection or dynamic dispatch

**BAD**:

```python
handler = getattr(service, f"handle_{event.kind}")
handler(event)
```

**GOOD** when the supported cases are fixed:

```python
match event.kind:
    case "created":
        service.handle_created(event)
    case "deleted":
        service.handle_deleted(event)
```

### C5. Prefer early returns to nesting

**BAD**:

```go
if user.Active {
    if user.Email != "" {
        send(user.Email)
    }
}
```

**GOOD**:

```go
if !user.Active {
    return
}
if user.Email == "" {
    return
}
send(user.Email)
```

### C6. Keep ternaries to simple assignments

**BAD**:

```javascript
const result = ready ? submit(build(payload)) : failed ? recover(error) : queue(payload);
```

**GOOD**:

```javascript
let result;
if (ready) {
  result = submit(build(payload));
} else if (failed) {
  result = recover(error);
} else {
  result = queue(payload);
}
```

A simple assignment remains fine: `const label = active ? "Active" : "Inactive";`.

### C7. Optimize for cognitive load, not character count

**BAD**:

```python
r = next((x.v for x in xs if x.k == k), d)
```

**GOOD**:

```python
result = default_value
for entry in entries:
    if entry.key == requested_key:
        result = entry.value
        break
```

### C8. Create constants only for meaning or synchronization

**BAD**:

```python
ONE = 1
page = current_page + ONE
```

**GOOD** when the name carries domain meaning:

```python
MAX_LOGIN_ATTEMPTS = 5
if failed_attempts >= MAX_LOGIN_ATTEMPTS:
    lock_account()
```

## Exceptions

### E1. Catch a specific exception only for meaningful recovery

**BAD**:

```python
try:
    config = load_config(path)
except Exception:
    config = {}
```

**GOOD** when a missing optional file has defined recovery:

```python
try:
    config = load_config(path)
except FileNotFoundError:
    config = default_config()
```

Otherwise omit the handler and let the failure propagate.

### E2. Do not swallow exceptions

**BAD**:

```python
try:
    save(record)
except DatabaseError:
    pass
```

**GOOD**:

```python
save(record)
```

### E3. Do not turn programmer errors into fallback values

**BAD**:

```python
try:
    return handlers[event.kind](event)
except KeyError:
    return None
```

**GOOD** — allow the invalid handler table or event kind to fail visibly:

```python
return handlers[event.kind](event)
```

### E4. Do not log and immediately rethrow without context

**BAD**:

```python
try:
    charge(card)
except PaymentError as error:
    logger.error("Payment failed: %s", error)
    raise
```

**GOOD**:

```python
charge(card)
```

Catch only when adding context that the caller could not otherwise obtain.

### E5. Do not retry without evidence

**BAD**:

```python
for _ in range(3):
    try:
        return client.create_order(order)
    except ApiError:
        continue
```

**GOOD** when no retry contract is established:

```python
return client.create_order(order)
```

### E6. Use conditionals for expected control flow

**BAD**:

```python
try:
    first_item = items[0]
except IndexError:
    first_item = None
```

**GOOD**:

```python
first_item = items[0] if items else None
```

Idiomatic EAFP is still good when it is genuinely the simpler form, such as a dictionary lookup whose missing-key recovery is the intended behavior.

## Testing

### T3. Derive expectations from the specification

**BAD** — repeat an implementation formula in the test:

```python
assert fee(100) == 100 * INTERNAL_FEE_RATE
```

**GOOD** — assert the externally specified outcome:

```python
assert fee(100) == Money("2.50")
```

### T4. Use Arrange-Act-Assert

**BAD**:

```python
def test_discount():
    cart = Cart()
    assert apply_discount(cart.add(Item(price=100)), "SAVE10").total == 90
```

**GOOD**:

```python
def test_discount():
    # Arrange
    cart = Cart([Item(price=100)])

    # Act
    discounted_cart = apply_discount(cart, "SAVE10")

    # Assert
    assert discounted_cart.total == 90
```

### T5. Test observable behavior, not trivial or coverage-only behavior

**BAD**:

```python
def test_name_getter_returns_name():
    user = User(name="Ada")
    assert user.name == "Ada"
```

**GOOD**:

```python
def test_duplicate_email_is_rejected():
    repository.insert(User(email="ada@example.com"))
    result = register(email="ada@example.com")
    assert result.error == "Email already registered"
```

The good test checks one observable, specified behavior with a plausible failure
path and protects against a realistic regression.
