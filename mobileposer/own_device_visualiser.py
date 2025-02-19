import torch
from contextlib import contextmanager
from mobileposer.config import *  # noqa: F403
from mobileposer.articulate.model import ParametricModel

@contextmanager
def load_predictions(pred_path):
    """Context manager for loading and cleaning up predictions."""
    try:
        predictions = torch.load(pred_path, map_location='cpu')
        yield predictions
    finally:
        # Ensure cleanup
        if 'predictions' in locals():
            del predictions
            torch.cuda.empty_cache()

@contextmanager
def create_parametric_model():
    """Context manager for SMPL model creation and cleanup."""
    model = None
    try:
        model = ParametricModel(paths.smpl_file, device='cpu')  # type: ignore # noqa: F405
        yield model
    finally:
        # Ensure cleanup
        if model is not None:
            del model
            torch.cuda.empty_cache()

def visualize_predictions(pred_path, output_path='output.mp4'):
    """Save the predictions to video file with proper resource management."""
    try:
        print(f"Processing predictions from: {pred_path}")
        
        with load_predictions(pred_path) as predictions:
            # Extract required data
            pose = predictions['pose'].cpu()
            translation = predictions['translation'].cpu()
            
            print(f"Loaded data - Pose shape: {pose.shape}, Translation shape: {translation.shape}")
            
            with create_parametric_model() as model:
                print(f"Starting to save motion sequence to {output_path}...")
                
                model.save_motion_sequence(
                    pose_list=[pose],
                    tran_list=[translation],
                    output_path=output_path,
                    fps=30
                )
                
                print(f"Motion sequence saved successfully to {output_path}")
    
    except Exception as e:
        print(f"Error in visualization process: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
