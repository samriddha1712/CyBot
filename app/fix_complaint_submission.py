"""
This file contains the fixed code for the complaint submission process.
"""

def enhanced_complaint_success(result):
    """Generate enhanced success message for complaint submission"""
    complaint_id = result['complaint_id']
    return f"""
    <div style="background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; margin: 15px 0; box-shadow: 0 3px 10px rgba(0,0,0,0.1); text-align: center;">
        <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
        <h3 style="margin-top: 0; margin-bottom: 15px; color: #155724;">Complaint Successfully Submitted!</h3>
        <div style="background-color: white; padding: 15px; border-radius: 8px; display: inline-block; margin: 10px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-family: monospace; font-size: 18px; letter-spacing: 1px;">
            {complaint_id}
        </div>
        <p style="margin-top: 15px; font-weight: bold;">Please save your complaint ID for future reference</p>
    </div>
    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-top: 15px; border-left: 4px solid #0077B6;">
        <h4 style="color: #0077B6; margin-top: 0;">What happens next?</h4>
        <ul style="margin-bottom: 0; padding-left: 20px;">
            <li>Our team will review your complaint within 1-2 business days</li>
            <li>You'll receive updates via the email address you provided</li>
            <li>You can check the status anytime using your complaint ID</li>
        </ul>
    </div>
    """

def enhanced_complaint_error(error_msg):
    """Generate enhanced error message for complaint submission"""
    return f"""
    <div style="background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; margin: 15px 0; box-shadow: 0 3px 10px rgba(0,0,0,0.1); text-align: center;">
        <div style="font-size: 48px; margin-bottom: 10px;">❌</div>
        <h3 style="margin-top: 0; margin-bottom: 15px; color: #721c24;">Submission Failed</h3>
        <p>We encountered an error while submitting your complaint:</p>
        <div style="background-color: white; color: #721c24; padding: 15px; border-radius: 8px; margin: 10px 0; font-family: monospace; text-align: left; overflow-wrap: break-word;">
            {error_msg}
        </div>
    </div>
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 15px; border-left: 4px solid #0077B6;">
        <h4 style="color: #0077B6; margin-top: 0;">Troubleshooting suggestions:</h4>
        <ul style="margin-bottom: 0; padding-left: 20px;">
            <li>Try submitting your complaint again</li>
            <li>Check your internet connection</li>
            <li>Contact our support team for assistance</li>
        </ul>
    </div>
    """
