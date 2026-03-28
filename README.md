# infracheck

Analyze software architecture for common design issues before they become production incidents.

infracheck reviews your infrastructure configuration and scores it across four categories:

- Fault Tolerance: DLQs, retries, Multi-AZ, backup policies
- Scalability: autoscaling, read replicas, bottlenecks
- Security: public access, open ingress, exposed databases
- Observability: CloudWatch alarms, log groups, tracing

## Usage

infracheck analyze ./infra

## Supported inputs

- Terraform (.tf files) - supported
- draw.io diagrams - planned
- Architecture images - planned

## Installation

pip install infracheck

## Status

Under active development.