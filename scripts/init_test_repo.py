"""Initialize test Git repository with Maven structure and sample commits."""
import os
import subprocess
from pathlib import Path

repo_dir = Path("tests/test_data/jenkins_test_repo")

# Already created by previous script
print(f"Using existing repo directory: {repo_dir}")

# Create pom.xml for Maven project
pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>jenkins-test</artifactId>
    <version>1.0.0</version>
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""

(repo_dir / "pom.xml").write_text(pom_content)

# Create sample Java source file
java_content = """package com.example.jcia;

public class Calculator {
    private int value = 0;

    public Calculator() {
        this.value = 0;
    }

    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public int getValue() {
        return value;
    }

    public void setValue(int value) {
        this.value = value;
    }
}
"""

(java_file := repo_dir / "src/main/java/com/example/jcia/Calculator.java")
java_file.parent.mkdir(parents=True, exist_ok=True)
java_file.write_text(java_content)

# Create test file
test_content = """package com.example.jcia;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CalculatorTest {
    @Test
    public void testAdd() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(2, 3));
    }

    @Test
    public void testSubtract() {
        Calculator calc = new Calculator();
        assertEquals(2, calc.subtract(5, 3));
    }

    @Test
    public void testMultiply() {
        Calculator calc = new Calculator();
        assertEquals(6, calc.multiply(2, 3));
    }

    @Test
    public void testGetValue() {
        Calculator calc = new Calculator();
        calc.setValue(42);
        assertEquals(42, calc.getValue());
    }
}
"""

(test) := repo_dir / "src/test/java/com/example/jcia/CalculatorTest.java"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text(test_content)

# Initialize Git repo
os.chdir(repo_dir)
subprocess.run(["git", "init"], check=True)

# Configure git
subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
subprocess.run(["git", "config", "user.name", "Test User"], check=True)

# Add all files
subprocess.run(["git", "add", "."], check=True)

# Create initial commit
subprocess.run([
    "git", "commit", "-m", "Initial commit: Add Calculator class and test"
], check=True)

# Create second commit with modification
java_content_v2 = """package com.example.jcia;

public class Calculator {
    private int value = 0;

    public Calculator() {
        this.value = 0;
    }

    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public int divide(int a, int b) {
        if (b == 0) {
            throw new IllegalArgumentException("Cannot divide by zero");
        }
        return a / b;
    }

    public int getValue() {
        return value;
    }

    public void setValue(int value) {
        this.value = value;
    }
}
"""

java_file.write_text(java_content_v2)
subprocess.run(["git", "add", "."], check=True)
subprocess.run([
    "git", "commit", "-m", "Add divide method to Calculator class"
], check=True)

# Create third commit - modify test
test_content_v2 = test_content.replace(
    "    public void testMultiply() {",
    "    public void testDivide() {\n        Calculator calc = new Calculator();\n        assertEquals(5, calc.divide(10, 2));\n    }\n\n    @Test"
)

test.write_text(test_content_v2)
subprocess.run(["git", "add", "."], check=True)
subprocess.run([
    "git", "commit", "-m", "Add divide test to CalculatorTest"
], check=True)

print("Created test Maven repository with 3 commits")
print(f"Java file: {java_file.relative_to(repo_dir)}")
print(f"Test file: {test.relative_to(repo_dir)}")
