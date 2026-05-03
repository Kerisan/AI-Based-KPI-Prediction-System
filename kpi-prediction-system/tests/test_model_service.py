"""
Unit tests for ModelService.
"""

import pytest
import numpy as np
from pathlib import Path

from services.model_service import ModelService
from services.data_service import DataService
from util.constants import ModelStatus


@pytest.fixture
def model_service():
    """Create ModelService instance."""
    return ModelService()


@pytest.fixture
def data_service():
    """Create DataService instance."""
    return DataService()


@pytest.fixture
def sample_dataset(data_service, tmp_path):
    """Create a sample dataset for testing."""
    dataset_path = data_service.generate_sample_dataset(
        dataset_name="test_dataset",
        num_records=200,
        target_column="traffic_count"
    )
    return dataset_path


class TestModelService:
    """Test cases for ModelService."""
    
    def test_build_lstm_model(self, model_service):
        """Test LSTM model building."""
        model = model_service.build_lstm_model(
            sequence_length=60,
            hidden_size=64,
            num_layers=2,
            dropout=0.2
        )
        
        assert model is not None
        assert len(model.layers) > 0
    
    def test_train_model_success(self, model_service, sample_dataset):
        """Test successful model training."""
        response = model_service.train_model(
            dataset_name="test_model",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            batch_size=16,
            sequence_length=30
        )
        
        assert response.status == ModelStatus.TRAINED
        assert response.metrics is not None
        assert response.model_path is not None
        
        # Cleanup
        model_service.delete_model("test_model")
    
    def test_train_model_invalid_file(self, model_service):
        """Test training with invalid file path."""
        response = model_service.train_model(
            dataset_name="test_invalid",
            file_path="nonexistent.csv",
            target_column="traffic_count",
            epochs=2
        )
        
        assert response.status == ModelStatus.FAILED
    
    def test_load_model(self, model_service, sample_dataset):
        """Test model loading."""
        # Train a model first
        model_service.train_model(
            dataset_name="test_load",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            sequence_length=30
        )
        
        # Load the model
        model = model_service.load_model("test_load")
        assert model is not None
        
        # Cleanup
        model_service.delete_model("test_load")
    
    def test_load_nonexistent_model(self, model_service):
        """Test loading non-existent model."""
        with pytest.raises(FileNotFoundError):
            model_service.load_model("nonexistent_model")
    
    def test_get_model_info(self, model_service, sample_dataset):
        """Test getting model information."""
        # Train a model
        model_service.train_model(
            dataset_name="test_info",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            sequence_length=30
        )
        
        # Get model info
        info = model_service.get_model_info("test_info")
        assert info.dataset_name == "test_info"
        assert info.status == ModelStatus.TRAINED
        
        # Cleanup
        model_service.delete_model("test_info")
    
    def test_list_models(self, model_service, sample_dataset):
        """Test listing models."""
        # Train a model
        model_service.train_model(
            dataset_name="test_list",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            sequence_length=30
        )
        
        # List models
        models = model_service.list_models()
        assert len(models) > 0
        
        # Cleanup
        model_service.delete_model("test_list")
    
    def test_delete_model(self, model_service, sample_dataset):
        """Test model deletion."""
        # Train a model
        model_service.train_model(
            dataset_name="test_delete",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            sequence_length=30
        )
        
        # Delete the model
        success = model_service.delete_model("test_delete")
        assert success is True
        
        # Verify deletion
        with pytest.raises(FileNotFoundError):
            model_service.load_model("test_delete")
    
    def test_predict(self, model_service, sample_dataset):
        """Test making predictions."""
        # Train a model
        model_service.train_model(
            dataset_name="test_predict",
            file_path=sample_dataset,
            target_column="traffic_count",
            epochs=2,
            sequence_length=30
        )
        
        # Create input sequence
        input_sequence = np.random.rand(1, 30, 1)
        
        # Make prediction
        prediction = model_service.predict("test_predict", input_sequence)
        assert isinstance(prediction, float)
        
        # Cleanup
        model_service.delete_model("test_predict")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
