import torch
from pathlib import Path
from mobileposer.viewers import SMPLViewer
from mobileposer.config import *  # noqa: F403
from mobileposer.articulate.model import ParametricModel

class PredictionViewer(SMPLViewer):
    """Extension of SMPLViewer for prediction-only visualization."""
    def view_predictions(self, pose_p, tran_p):
        """View only predictions without ground truth."""
        # Create dummy data matching prediction shape for ground truth
        n_frames = pose_p.shape[0]
        pose_t = torch.zeros_like(pose_p)
        tran_t = torch.zeros_like(tran_p)
        
        super().view(pose_p, tran_p, pose_t, tran_t, with_tran=True)

def visualize_predictions(pred_path):
    """Visualize and save the predictions using SMPLViewer."""
    # Load predictions
    print("Loading predictions from:", pred_path)
    predictions = torch.load(pred_path, map_location='cpu')
    
    # Extract the predicted poses and translations
    pose = predictions.get('pose')
    translation = predictions.get('translation')
    
    if pose is None:
        raise ValueError("No pose data found in predictions")
    if translation is None:
        raise ValueError("No translation data found in predictions")
    
    # Initialize the parametric model
    model = ParametricModel(paths.smpl_file)
    
    # View and save the motion - this will create 'a.mp4' in your current directory
    model.view_motion(
        pose_list=[pose],        # List of pose tensors
        tran_list=[translation], # List of translation tensors
        fps=30,                  # Frame rate of output video
        distance_between_subjects=0.8  # Space between subjects if showing multiple
    )
    
    print("\nVisualization saved as 'a.mp4' in the current directory")

if __name__ == "__main__":
    # Path to your predictions file
    pred_path = Path("data/processed_datasets/predictions.pt")
    
    if not pred_path.exists():
        print(f"Error: Predictions file not found at {pred_path}")
        print("Make sure you have generated predictions.pt first.")
        exit(1)
    
    try:
        visualize_predictions(pred_path)
    except FileNotFoundError as e:
        print(f"\nError: {str(e)}")
        print("\nPlease download the SMPL model file and place it at the correct location.")
        print("1. Register and download from https://smpl.is.tue.mpg.de/")
        print("2. Place basicmodel_m.pkl in the smpl/ directory")
    except Exception as e:
        print(f"\nError visualizing predictions: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting steps:")
        print("1. Make sure all dependencies are installed (pip install -r requirements.txt)")
        print("2. Verify predictions.pt was generated successfully")