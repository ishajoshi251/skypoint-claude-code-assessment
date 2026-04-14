# Claude Development Guide

## Purpose

This project is designed to quickly generate a production-ready backend system during a live assessment using Claude Code.

## Approach

* Start with a minimal, working, dockerized system
* Build incrementally
* Focus on correctness > optimization initially

## Tech Stack (Default)

* Backend: Python (FastAPI)
* Database: PostgreSQL
* Containerization: Docker + Docker Compose

## Principles

* Clean architecture (routes → services → models)
* Environment-based configuration
* Scalable folder structure
* Minimal but extensible code

## Expectations from Claude

* Always generate runnable code
* Always include Docker setup
* Always include README
* Prefer clarity over cleverness

## Execution Strategy During Assessment

1. Understand problem
2. Create working API
3. Add database integration
4. Dockerize everything
5. Validate end-to-end flow
