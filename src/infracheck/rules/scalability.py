from infracheck.models import RuleResult

CATEGORY = "scalability"


def check_autoscaling_configured(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """There should be at least one autoscaling group defined."""
    has_asg = len(resources.get("aws_autoscaling_group", [])) > 0
    return [
        RuleResult(
            rule_id="autoscaling_configured",
            category=CATEGORY,
            severity="medium",
            passed=has_asg,
            message="At least one autoscaling group is configured"
            if has_asg
            else "No autoscaling groups found - compute cannot scale automatically under load",
        )
    ]


def check_autoscaling_elb_health_check(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """ASGs attached to a load balancer should use ELB health checks, not EC2 health checks."""
    results = []

    for asg in resources.get("aws_autoscaling_group", []):
        is_attached_to_lb = bool(asg.get("target_group_arns") or asg.get("load_balancers"))

        if is_attached_to_lb:
            uses_elb_health_check = asg.get("health_check_type", "EC2") == "ELB"
            results.append(
                RuleResult(
                    rule_id="autoscaling_elb_health_check",
                    category=CATEGORY,
                    severity="high",
                    passed=uses_elb_health_check,
                    message="Autoscaling group uses ELB health checks"
                    if uses_elb_health_check
                    else "Autoscaling group uses EC2 health checks - unhealthy instances"
                    " may stay in rotation when attached to a load balancer",
                    resource=asg["_name"],
                )
            )

    return results


def check_lambda_reserved_concurrency(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """Lambda functions should have a reserved concurrency limit set."""
    results = []

    for function in resources.get("aws_lambda_function", []):
        # -1 means no limit set; 0 disables the function entirely
        concurrency = function.get("reserved_concurrent_executions", -1)
        has_limit = concurrency > 0
        results.append(
            RuleResult(
                rule_id="lambda_reserved_concurrency",
                category=CATEGORY,
                severity="high",
                passed=has_limit,
                message="Lambda function has a reserved concurrency limit"
                if has_limit
                else "Lambda function has no reserved concurrency limit - it can exhaust"
                " the account-wide concurrency quota and throttle other functions",
                resource=function["_name"],
            )
        )

    return results


def check_elasticache_automatic_failover(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """ElastiCache replication groups should have automatic failover enabled."""
    results = []

    for replication_group in resources.get("aws_elasticache_replication_group", []):
        has_failover = replication_group.get("automatic_failover_enabled", False)
        results.append(
            RuleResult(
                rule_id="elasticache_automatic_failover",
                category=CATEGORY,
                severity="medium",
                passed=has_failover,
                message="ElastiCache replication group has automatic failover enabled"
                if has_failover
                else "ElastiCache replication group does not have automatic failover enabled"
                " - the cluster will go offline if the primary node fails",
                resource=replication_group["_name"],
            )
        )

    return results


def check_elasticache_cluster_size(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """ElastiCache replication groups should have at least 2 nodes for read scaling."""
    results = []
    minimum_nodes = 2

    for replication_group in resources.get("aws_elasticache_replication_group", []):
        node_count = replication_group.get("num_cache_clusters", 1)
        has_sufficient_nodes = node_count >= minimum_nodes
        results.append(
            RuleResult(
                rule_id="elasticache_cluster_size",
                category=CATEGORY,
                severity="medium",
                passed=has_sufficient_nodes,
                message=f"ElastiCache replication group has {node_count} nodes"
                if has_sufficient_nodes
                else f"ElastiCache replication group has only {node_count} node(s)"
                f" - minimum {minimum_nodes} recommended for read scaling",
                resource=replication_group["_name"],
            )
        )

    return results


def check_elasticache_backup_retention(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """ElastiCache Redis clusters should retain snapshots for at least 1 day."""
    results = []
    minimum_retention_days = 1

    for replication_group in resources.get("aws_elasticache_replication_group", []):
        retention_days = replication_group.get("snapshot_retention_limit", 0)
        has_backups = retention_days >= minimum_retention_days
        results.append(
            RuleResult(
                rule_id="elasticache_backup_retention",
                category=CATEGORY,
                severity="medium",
                passed=has_backups,
                message=f"ElastiCache replication group retains snapshots for {retention_days} days"
                if has_backups
                else "ElastiCache replication group has no snapshot retention configured"
                " — data will be lost if the cluster fails",
                resource=replication_group["_name"],
            )
        )

    return results


def check_load_balancer_cross_zone(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """Load balancers should have cross-zone load balancing enabled."""
    results = []

    for load_balancer in resources.get("aws_lb", []):
        # ALBs have cross-zone enabled by default; NLBs and GWLBs do not
        lb_type = load_balancer.get("load_balancer_type", "application")
        if lb_type in ("network", "gateway"):
            has_cross_zone = load_balancer.get("enable_cross_zone_load_balancing", False)
            results.append(
                RuleResult(
                    rule_id="load_balancer_cross_zone",
                    category=CATEGORY,
                    severity="medium",
                    passed=has_cross_zone,
                    message="Load balancer has cross-zone load balancing enabled"
                    if has_cross_zone
                    else "Load balancer does not have cross-zone load balancing enabled"
                    " - traffic will be unevenly distributed across availability zones",
                    resource=load_balancer["_name"],
                )
            )

    return results


def check_rds_read_replicas(resources: dict[str, list[dict]]) -> list[RuleResult]:
    """RDS instances under read-heavy workloads should have read replicas."""
    results = []

    for instance in resources.get("aws_db_instance", []):
        # A read replica is defined by setting replicate_source_db on a separate instance
        is_replica = "replicate_source_db" in instance
        has_replica = any(
            "replicate_source_db" in other
            for other in resources.get("aws_db_instance", [])
            if other["_name"] != instance["_name"]
        )

        # Only flag primary instances (not the replicas themselves)
        if not is_replica:
            results.append(
                RuleResult(
                    rule_id="rds_read_replicas",
                    category=CATEGORY,
                    severity="low",
                    passed=has_replica,
                    message="RDS instance has a read replica configured"
                    if has_replica
                    else "RDS instance has no read replicas - consider adding one"
                    " for read-heavy workloads",
                    resource=instance["_name"],
                )
            )

    return results
