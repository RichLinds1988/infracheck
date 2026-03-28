from infracheck.rules.scalability import (
    check_autoscaling_configured,
    check_autoscaling_elb_health_check,
    check_elasticache_automatic_failover,
    check_elasticache_backup_retention,
    check_elasticache_cluster_size,
    check_lambda_reserved_concurrency,
    check_load_balancer_cross_zone,
    check_rds_read_replicas,
)


class TestAutoscalingConfigured:
    def test_passes_when_asg_exists(self):
        resources = {"aws_autoscaling_group": [{"_name": "my_asg", "min_size": 1, "max_size": 5}]}
        results = check_autoscaling_configured(resources)
        assert results[0].passed is True

    def test_fails_when_no_asg(self):
        results = check_autoscaling_configured({})
        assert results[0].passed is False


class TestAutoscalingElbHealthCheck:
    def test_passes_when_elb_health_check_configured(self):
        resources = {
            "aws_autoscaling_group": [
                {
                    "_name": "my_asg",
                    "target_group_arns": ["arn:aws:..."],
                    "health_check_type": "ELB",
                }
            ]
        }
        results = check_autoscaling_elb_health_check(resources)
        assert results[0].passed is True

    def test_fails_when_ec2_health_check_used_with_lb(self):
        resources = {
            "aws_autoscaling_group": [
                {
                    "_name": "my_asg",
                    "target_group_arns": ["arn:aws:..."],
                    "health_check_type": "EC2",
                }
            ]
        }
        results = check_autoscaling_elb_health_check(resources)
        assert results[0].passed is False

    def test_skips_asg_not_attached_to_lb(self):
        resources = {"aws_autoscaling_group": [{"_name": "my_asg"}]}
        results = check_autoscaling_elb_health_check(resources)
        assert results == []

    def test_returns_empty_when_no_asgs(self):
        results = check_autoscaling_elb_health_check({})
        assert results == []


class TestLambdaReservedConcurrency:
    def test_passes_when_concurrency_limit_set(self):
        resources = {
            "aws_lambda_function": [{"_name": "my_func", "reserved_concurrent_executions": 100}]
        }
        results = check_lambda_reserved_concurrency(resources)
        assert results[0].passed is True

    def test_fails_when_no_concurrency_limit(self):
        resources = {"aws_lambda_function": [{"_name": "my_func"}]}
        results = check_lambda_reserved_concurrency(resources)
        assert results[0].passed is False

    def test_fails_when_concurrency_is_minus_one(self):
        resources = {
            "aws_lambda_function": [{"_name": "my_func", "reserved_concurrent_executions": -1}]
        }
        results = check_lambda_reserved_concurrency(resources)
        assert results[0].passed is False

    def test_fails_when_concurrency_is_zero(self):
        resources = {
            "aws_lambda_function": [{"_name": "my_func", "reserved_concurrent_executions": 0}]
        }
        results = check_lambda_reserved_concurrency(resources)
        assert results[0].passed is False

    def test_returns_empty_when_no_functions(self):
        results = check_lambda_reserved_concurrency({})
        assert results == []


class TestElasticacheAutomaticFailover:
    def test_passes_when_automatic_failover_enabled(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "automatic_failover_enabled": True,
                }
            ]
        }
        results = check_elasticache_automatic_failover(resources)
        assert results[0].passed is True

    def test_fails_when_automatic_failover_disabled(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "automatic_failover_enabled": False,
                }
            ]
        }
        results = check_elasticache_automatic_failover(resources)
        assert results[0].passed is False

    def test_fails_when_automatic_failover_not_set(self):
        resources = {"aws_elasticache_replication_group": [{"_name": "my_cache"}]}
        results = check_elasticache_automatic_failover(resources)
        assert results[0].passed is False

    def test_returns_empty_when_no_replication_groups(self):
        results = check_elasticache_automatic_failover({})
        assert results == []


class TestElasticacheBackupRetention:
    def test_passes_when_snapshot_retention_set(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "snapshot_retention_limit": 7,
                }
            ]
        }
        results = check_elasticache_backup_retention(resources)
        assert results[0].passed is True

    def test_fails_when_snapshot_retention_is_zero(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "snapshot_retention_limit": 0,
                }
            ]
        }
        results = check_elasticache_backup_retention(resources)
        assert results[0].passed is False

    def test_fails_when_snapshot_retention_not_set(self):
        resources = {"aws_elasticache_replication_group": [{"_name": "my_cache"}]}
        results = check_elasticache_backup_retention(resources)
        assert results[0].passed is False

    def test_returns_empty_when_no_replication_groups(self):
        results = check_elasticache_backup_retention({})
        assert results == []


class TestElasticacheClusterSize:
    def test_passes_when_cluster_has_enough_nodes(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "num_cache_clusters": 2,
                }
            ]
        }
        results = check_elasticache_cluster_size(resources)
        assert results[0].passed is True

    def test_fails_when_cluster_has_one_node(self):
        resources = {
            "aws_elasticache_replication_group": [
                {
                    "_name": "my_cache",
                    "num_cache_clusters": 1,
                }
            ]
        }
        results = check_elasticache_cluster_size(resources)
        assert results[0].passed is False

    def test_fails_when_num_cache_clusters_not_set(self):
        resources = {"aws_elasticache_replication_group": [{"_name": "my_cache"}]}
        results = check_elasticache_cluster_size(resources)
        assert results[0].passed is False

    def test_returns_empty_when_no_replication_groups(self):
        results = check_elasticache_cluster_size({})
        assert results == []


class TestLoadBalancerCrossZone:
    def test_passes_when_cross_zone_enabled_on_nlb(self):
        resources = {
            "aws_lb": [
                {
                    "_name": "my_nlb",
                    "load_balancer_type": "network",
                    "enable_cross_zone_load_balancing": True,
                }
            ]
        }
        results = check_load_balancer_cross_zone(resources)
        assert results[0].passed is True

    def test_fails_when_cross_zone_disabled_on_nlb(self):
        resources = {
            "aws_lb": [
                {
                    "_name": "my_nlb",
                    "load_balancer_type": "network",
                    "enable_cross_zone_load_balancing": False,
                }
            ]
        }
        results = check_load_balancer_cross_zone(resources)
        assert results[0].passed is False

    def test_skips_application_load_balancers(self):
        resources = {
            "aws_lb": [
                {
                    "_name": "my_alb",
                    "load_balancer_type": "application",
                }
            ]
        }
        results = check_load_balancer_cross_zone(resources)
        assert results == []

    def test_returns_empty_when_no_load_balancers(self):
        results = check_load_balancer_cross_zone({})
        assert results == []


class TestRdsReadReplicas:
    def test_passes_when_read_replica_exists(self):
        resources = {
            "aws_db_instance": [
                {"_name": "primary_db"},
                {"_name": "replica_db", "replicate_source_db": "primary_db"},
            ]
        }
        results = check_rds_read_replicas(resources)
        assert results[0].passed is True

    def test_fails_when_no_read_replica(self):
        resources = {"aws_db_instance": [{"_name": "primary_db"}]}
        results = check_rds_read_replicas(resources)
        assert results[0].passed is False

    def test_replica_instances_are_not_checked(self):
        resources = {
            "aws_db_instance": [
                {"_name": "primary_db"},
                {"_name": "replica_db", "replicate_source_db": "primary_db"},
            ]
        }
        results = check_rds_read_replicas(resources)
        assert len(results) == 1
        assert results[0].resource == "primary_db"

    def test_returns_empty_when_no_instances(self):
        results = check_rds_read_replicas({})
        assert results == []
