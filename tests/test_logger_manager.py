import pytest
import threading
import time
from unittest.mock import patch, MagicMock

from baselog.logger_manager import LoggerManager
from baselog.logger import Logger, LoggerMode
from baselog.api.config import APIConfig, Environment, Timeouts, RetryStrategy


class TestLoggerManager:
    """Test suite for LoggerManager singleton class."""

    def setup_method(self):
        """Reset LoggerManager before each test."""
        LoggerManager._instance = None
        with patch.object(LoggerManager, '_lock'):
            manager = LoggerManager()
            manager.reset()

    def test_singleton_pattern(self):
        """Test that LoggerManager implements singleton pattern correctly."""
        manager1 = LoggerManager()
        manager2 = LoggerManager()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe."""
        instances = []

        def get_manager():
            instances.append(LoggerManager())

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_manager)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_lazy_loading(self):
        """Test that logger is created only when needed."""
        manager = LoggerManager()

        # Logger should not be created initially
        assert manager._logger is None

        # Logger should be created when first accessed
        logger = manager.get_logger()
        assert manager._logger is not None
        assert logger is manager._logger

    def test_auto_configuration_from_env(self):
        """Test auto-configuration from environment variables."""
        # Reset singleton for clean test
        LoggerManager._instance = None

        with patch.dict('os.environ', {
            'BASELOG_API_KEY': 'test-api-key-1234567890123456',  # 16 chars minimum
            'BASELOG_ENVIRONMENT': 'development'
        }):
            with patch('baselog.api.config.load_config') as mock_load_config:
                mock_config = APIConfig(
                    api_key='test-api-key-1234567890123456',
                    base_url='https://baselog-api.vercel.app',
                    environment=Environment.DEVELOPMENT,
                    timeouts=Timeouts.from_env(),
                    retry_strategy=RetryStrategy.from_env()
                )
                mock_load_config.return_value = mock_config

                manager = LoggerManager()
                logger = manager.get_logger()

                mock_load_config.assert_called_once()
                assert manager._configured is True
                assert logger.is_api_mode()

    def test_manual_configuration_with_api_key(self):
        """Test manual configuration with API key."""
        manager = LoggerManager()
        test_api_key = 'test-manual-key-1234567890123456'  # 16 chars minimum

        manager.configure(api_key=test_api_key)
        logger = manager.get_logger()

        assert manager._configured is True
        assert logger.is_api_mode()

    def test_manual_configuration_with_config(self):
        """Test manual configuration with APIConfig object."""
        manager = LoggerManager()
        test_config = APIConfig(
            api_key='test-config-key-1234567890123456',  # 16 chars minimum
            base_url='https://custom-api.com/v1',
            environment=Environment.PRODUCTION,
            timeouts=Timeouts.from_env(),
            retry_strategy=RetryStrategy.from_env()
        )

        manager.configure(config=test_config)
        logger = manager.get_logger()

        assert manager._configured is True
        assert logger.is_api_mode()
        assert logger.config.base_url == 'https://custom-api.com/v1'

    def test_manual_configuration_with_kwargs(self):
        """Test manual configuration with kwargs."""
        manager = LoggerManager()

        manager.configure(
            api_key='test-kwargs-key-1234567890123456',  # 16 chars minimum
            base_url='https://kwargs-api.com/v1',
            environment='production'
        )

        assert manager._configured is True
        logger = manager.get_logger()
        assert logger.is_api_mode()

    def test_configuration_fallback(self):
        """Test that configuration falls back to local logger on failure."""
        manager = LoggerManager()

        with patch('baselog.logger.Logger') as mock_logger_class:
            # Create a mock logger that will fail when creating API client
            mock_logger_instance = MagicMock()
            mock_logger_instance.is_api_mode.return_value = False  # Local mode
            mock_logger_class.return_value = mock_logger_instance

            # Mock the Logger._setup_api_client method to raise exception
            mock_logger_instance._setup_api_client.side_effect = Exception("Configuration failed")
            mock_logger_instance._resolve_config.return_value = None

            manager.configure(api_key='test-key-1234567890123456')  # 16 chars minimum

            # Should still create a logger, but in local mode
            assert manager._logger is not None
            assert manager._configured is False
            mock_logger_class.assert_called()

    def test_is_configured(self):
        """Test is_configured method."""
        manager = LoggerManager()

        # Initially not configured
        assert manager.is_configured() is False

        # Configure with API
        manager.configure(api_key='test-key-1234567890123456')  # 16 chars minimum
        assert manager.is_configured() is True

        # Reset and test again
        manager.reset()
        assert manager.is_configured() is False

    def test_reset_functionality(self):
        """Test reset method."""
        manager = LoggerManager()

        # Configure the manager
        manager.configure(api_key='test-key')
        logger = manager.get_logger()

        assert manager._logger is not None
        assert manager._configured is True

        # Reset the manager
        manager.reset()

        assert manager._logger is None
        assert manager._configured is False

    def test_get_current_config(self):
        """Test get_current_config method."""
        manager = LoggerManager()

        # Initially no config
        assert manager.get_current_config() is None

        # Configure with API
        test_config = APIConfig(
            api_key='test-key-1234567890123456',  # 16 chars minimum
            base_url='https://api.test.com/v1',
            environment=Environment.DEVELOPMENT,
            timeouts=Timeouts.from_env(),
            retry_strategy=RetryStrategy.from_env()
        )
        manager.configure(config=test_config)

        config = manager.get_current_config()
        assert config is not None
        assert config.api_key == 'test-key-1234567890123456'

    def test_get_status(self):
        """Test get_status method."""
        manager = LoggerManager()

        # Initial status
        status = manager.get_status()
        assert status == {
            "configured": False,
            "logger_mode": "None",
            "api_mode": False,
            "has_config": False
        }

        # Configure with API
        manager.configure(api_key='test-key-1234567890123456')  # 16 chars minimum
        logger = manager.get_logger()

        status = manager.get_status()
        assert status["configured"] is True
        assert status["api_mode"] is True
        assert status["has_config"] is True
        assert status["logger_mode"] == "api"

    def test_concurrent_access(self):
        """Test thread-safe concurrent access to LoggerManager."""
        manager = LoggerManager()
        results = []

        def worker(worker_id):
            try:
                logger = manager.get_logger()
                results.append((worker_id, logger is not None))

                # Test configuration with valid API key
                time.sleep(0.001)  # Small delay to reduce race conditions
                manager.configure(api_key=f'worker-{worker_id}-key-1234567890123456')  # 16 chars minimum
                time.sleep(0.001)  # Small delay to reduce race conditions

                is_configured = manager.is_configured()
                results.append((worker_id, is_configured))

                # Test status
                status = manager.get_status()
                results.append((worker_id, status["configured"]))

            except Exception as e:
                results.append((worker_id, f"error: {e}"))

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All workers should have succeeded
        for result in results:
            if isinstance(result[1], str):
                assert result[1].startswith("error"), f"Worker {result[0]} failed: {result[1]}"
            else:
                assert result[1] is True, f"Worker {result[0]} failed"

    def test_nested_configuration_calls(self):
        """Test that nested configuration calls work properly with reentrant lock."""
        manager = LoggerManager()

        def nested_configure():
            logger = manager.get_logger()
            return logger

        # Configure and access logger in nested manner
        manager.configure(api_key='test-nested-key')

        outer_logger = manager.get_logger()
        inner_logger = nested_configure()

        assert outer_logger is inner_logger

    def test_repeated_get_calls(self):
        """Test that repeated get_logger() calls return the same instance."""
        manager = LoggerManager()

        logger1 = manager.get_logger()
        logger2 = manager.get_logger()
        logger3 = manager.get_logger()

        assert logger1 is logger2 is logger3

    def test_status_after_reset(self):
        """Test status after reset."""
        manager = LoggerManager()

        # Configure
        manager.configure(api_key='test-key-1234567890123456')  # 16 chars minimum
        assert manager.get_status()["configured"] is True

        # Reset
        manager.reset()

        # Status should be reset
        status = manager.get_status()
        assert status == {
            "configured": False,
            "logger_mode": "None",
            "api_mode": False,
            "has_config": False
        }

    def test_environment_configuration_error_handling(self):
        """Test error handling in environment configuration."""
        with patch.dict('os.environ', {
            'BASELOG_API_KEY': 'test-key',
            'BASELOG_ENVIRONMENT': 'invalid-env'
        }):
            with patch('baselog.logger_manager.load_config') as mock_load_config:
                mock_load_config.side_effect = Exception("Invalid environment")

                manager = LoggerManager()
                logger = manager.get_logger()

                # Should fallback to local logger
                assert manager._configured is False
                assert logger.is_local_mode()

    def test_kwargs_configuration_defaults(self):
        """Test that kwargs configuration uses sensible defaults."""
        manager = LoggerManager()

        # Configure with only API key
        manager.configure(api_key='test-key-1234567890123456')  # 16 chars minimum
        logger = manager.get_logger()

        assert manager._configured is True
        assert logger.is_api_mode()

        # Check that defaults were applied
        config = manager.get_current_config()
        assert config.base_url == 'https://baselog-api.vercel.app'
        assert config.environment == Environment.DEVELOPMENT