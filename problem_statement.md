# CDF Shadow AI Hackathon - Submission Guide

## Challenge Overview

This hackathon asks participants to build a **"Shadow AI Privacy Auditor"** - a tool that helps users identify and remove sensitive or confidential information from their text **before** they share it with a public AI tool such as ChatGPT, Gemini, or Copilot. The evaluation framework prioritizes accuracy of sensitive-information detection (30%), usability and clarity (20%), responsible privacy and security design (20%), creativity and practical value (15%), and presentation and demonstration (15%).

## Core Tier 1 Requirements

**Text Input:** The tool must let a user paste or type the text they intend to send to an AI platform. A basic, usable interface is required - a simple web application is sufficient.

**Detection Engine:** The system must detect **at least four of six** categories of sensitive information: (1) names and contact information; (2) government or financial identifiers; (3) passwords, API keys, or access credentials; (4) medical or sensitive personal information; (5) employee, client, or volunteer information; (6) confidential organizational or project information. Teams may use pattern matching, regular expressions, existing libraries, AI models, or a combination - training a new model is not required.

**Highlighting & Explanation:** Detected information must be **visually highlighted**, categorized, and accompanied by a short explanation of why it may be risky.

**Review & Redaction:** The user must be able to review the findings and generate a **safer, redacted version** of the text (for example `[NAME]`, `[EMAIL]`, `[EMPLOYEE ID]`). The tool must **not** over-redact - safe sentences such as "The project meeting is scheduled for 3:00 PM" must remain unchanged.

**Testing:** The solution must be tested with **at least 10 team-created fictional test cases**, including safe examples that demonstrate the tool does not redact everything unnecessarily.

**Responsible Data Use:** Teams must use only fictional or synthetic examples. Teams must **not** collect, store, or use real personal, medical, financial, immigration, employee, volunteer, or organizational data.

## Tier 2 Stretch Goals

A browser extension, direct integration with AI platforms, additional detection categories, machine-learning or NER-based detection, multilingual detection, real-time monitoring, severity or risk scoring, one-click "copy safe text," undo/keep controls, and configurable custom rules differentiate stronger submissions.

## Submission Requirements

Participants must provide a working prototype and its code in a repository, a short explanation of how the detection works, at least 10 fictional test cases and their results, a list of known limitations and future improvements, a live deployment URL, and a 3–5 minute walkthrough video covering the detection approach, the redaction of a risky example, correct handling of a safe example, AI usage, and limitations.

**Deadline:** Firm. A well-executed Tier 1 submission outweighs incomplete attempts at all tiers.
