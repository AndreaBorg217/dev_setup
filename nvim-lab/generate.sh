#!/usr/bin/env bash
# Materializes the 4 throwaway lab projects under ~/tmp/nvim-next-lab.
# Safe to re-run: wipes and recreates the lab root each time.
set -euo pipefail

LAB_ROOT="${LAB_ROOT:-$HOME/tmp/nvim-next-lab}"

rm -rf "$LAB_ROOT"
mkdir -p "$LAB_ROOT"/{java-spring,python,go,misc}

# --- java-spring -------------------------------------------------------

mkdir -p "$LAB_ROOT/java-spring/src/main/java/com/example/demo"
mkdir -p "$LAB_ROOT/java-spring/src/main/resources"
mkdir -p "$LAB_ROOT/java-spring/src/test/java/com/example/demo"

cat > "$LAB_ROOT/java-spring/pom.xml" <<'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
EOF

cat > "$LAB_ROOT/java-spring/src/main/resources/application.yml" <<'EOF'
demo:
  greeting: Hello
  max-greetings: 5
server:
  port: 8080
EOF

cat > "$LAB_ROOT/java-spring/src/main/java/com/example/demo/DemoApplication.java" <<'EOF'
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
EOF

cat > "$LAB_ROOT/java-spring/src/main/java/com/example/demo/GreetingService.java" <<'EOF'
package com.example.demo;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class GreetingService {

    @Value("${demo.greeting}")
    private String greeting;

    public String greet(String name) {
        return greeting + ", " + name + "!";
    }
}
EOF

cat > "$LAB_ROOT/java-spring/src/main/java/com/example/demo/HelloController.java" <<'EOF'
package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    private final GreetingService greetingService;

    public HelloController(GreetingService greetingService) {
        this.greetingService = greetingService;
    }

    @GetMapping("/hello")
    public String hello(@RequestParam(defaultValue = "world") String name) {
        return greetingService.greet(name);
    }
}
EOF

cat > "$LAB_ROOT/java-spring/src/main/java/com/example/demo/DemoProperties.java" <<'EOF'
package com.example.demo;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "demo")
public class DemoProperties {

    private String greeting;
    private int maxGreetings;

    public String getGreeting() {
        return greeting;
    }

    public void setGreeting(String greeting) {
        this.greeting = greeting;
    }

    public int getMaxGreetings() {
        return maxGreetings;
    }

    public void setMaxGreetings(int maxGreetings) {
        this.maxGreetings = maxGreetings;
    }
}
EOF

# Planted compile error: undefined method call, isolated to this file so the
# rest of the module (used for rename/format/action tests) still parses.
cat > "$LAB_ROOT/java-spring/src/main/java/com/example/demo/ScheduledTasks.java" <<'EOF'
package com.example.demo;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class ScheduledTasks {

    @Scheduled(cron = "0 0 * * * *")
    public void hourlyTask() {
        int result = thisMethodDoesNotExist();
    }
}
EOF

cat > "$LAB_ROOT/java-spring/src/test/java/com/example/demo/GreetingServiceTest.java" <<'EOF'
package com.example.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GreetingServiceTest {

    @Test
    void greetsByName() {
        GreetingService service = new GreetingService();
        assertEquals("Hello, world!", service.greet("world"));
    }
}
EOF

# --- python --------------------------------------------------------------

cat > "$LAB_ROOT/python/pyproject.toml" <<'EOF'
[project]
name = "lab"
version = "0.0.1"
requires-python = ">=3.11"

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["ALL"]
ignore = ["CPY001"]
EOF

# Planted ruff violation: unused import (F401).
# Planted type error: str assigned where an int-annotated variable is declared.
cat > "$LAB_ROOT/python/greeter.py" <<'EOF'
import os

def greet(name: str) -> str:
    count: int = "not a number"
    return f"Hello, {name}! ({count})"


def add(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    print(greet("world"))
    print(add(2, 3))
EOF

# --- go --------------------------------------------------------------------

cat > "$LAB_ROOT/go/go.mod" <<'EOF'
module lab

go 1.22
EOF

# Planted lint-only issue (ineffassign, bundled in golangci-lint's default
# linter set): the first assignment to `result` is overwritten before it is
# ever read, but `result` itself is read later, so this compiles cleanly and
# only a linter (not the Go compiler) flags it.
cat > "$LAB_ROOT/go/main.go" <<'EOF'
package main

import "fmt"

func add(a int, b int) int {
	return a + b
}

func main() {
	result := add(2, 3)
	result = add(4, 5)
	fmt.Println(result)
}
EOF

cat > "$LAB_ROOT/go/main_test.go" <<'EOF'
package main

import "testing"

func TestAdd(t *testing.T) {
	if add(2, 3) != 5 {
		t.Fatal("add(2, 3) should be 5")
	}
}
EOF

# --- misc --------------------------------------------------------------------

cat > "$LAB_ROOT/misc/sample.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo   "hello"
EOF

cat > "$LAB_ROOT/misc/Dockerfile" <<'EOF'
FROM alpine:3.20
RUN    apk add --no-cache curl
CMD ["/bin/sh"]
EOF

cat > "$LAB_ROOT/misc/sample.json" <<'EOF'
{
"name":"lab",   "version":  1
}
EOF

cat > "$LAB_ROOT/misc/sample.lua" <<'EOF'
local function greet(name)
  return   "hello "..name
end
return greet
EOF

cat > "$LAB_ROOT/misc/sample.md" <<'EOF'
# Sample

This    is a  sample markdown file.

*   item one
*   item two
EOF

cat > "$LAB_ROOT/misc/sample.yaml" <<'EOF'
name:    lab
items:
  -   one
  -   two
EOF

echo "Generated lab projects under $LAB_ROOT"
