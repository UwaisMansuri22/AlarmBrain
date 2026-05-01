import json
import boto3
from datetime import datetime
from pathlib import Path

from app.models import IncidentBrief


class IncidentStorage:
    """
    Stores incident briefs to S3 in a date-partitioned structure.
    
    Path pattern: incident_history/YYYY/MM/DD/incident_id.json
    
    This mirrors how real log archives work — queryable by date, 
    easily archived, and fits S3's prefix-based access patterns.
    """
    
    def __init__(self, bucket_name: str = None):
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name or "alarmbrain-incidents"
        
    def save(self, brief: IncidentBrief) -> str:
        """
        Save an incident brief to S3.
        
        Returns the S3 key (path) where the brief was stored.
        """
        
        # Generate S3 key: incident_history/YYYY/MM/DD/incident_id.json
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        key = f"incident_history/{year}/{month}/{day}/{brief.incident_id}.json"
        
        # Convert brief to JSON
        body = json.dumps(brief.dict(), indent=2)
        
        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType="application/json"
            )
            print(f"Saved incident brief to s3://{self.bucket_name}/{key}")
            return key
        except Exception as e:
            print(f"Error saving to S3: {e}")
            raise
    
    def get_incidents_by_date(self, year: str, month: str, day: str) -> list[dict]:
        """
        Retrieve all incidents for a specific date.
        
        Args:
            year: YYYY format
            month: MM format
            day: DD format
        
        Returns:
            List of incident briefs as dicts
        """
        
        prefix = f"incident_history/{year}/{month}/{day}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            incidents = []
            if "Contents" not in response:
                return incidents
            
            for obj in response["Contents"]:
                file_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=obj["Key"]
                )
                body = file_response["Body"].read().decode("utf-8")
                incident = json.loads(body)
                incidents.append(incident)
            
            return incidents
        except Exception as e:
            print(f"Error retrieving incidents from S3: {e}")
            return []
    
    def get_incident_by_id(self, incident_id: str, year: str, month: str, day: str) -> dict:
        """
        Retrieve a specific incident brief by ID and date.
        
        Args:
            incident_id: The incident ID (e.g., INC-ABC123)
            year: YYYY format
            month: MM format
            day: DD format
        
        Returns:
            Incident brief as dict, or None if not found
        """
        
        key = f"incident_history/{year}/{month}/{day}/{incident_id}.json"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            body = response["Body"].read().decode("utf-8")
            return json.loads(body)
        except self.s3_client.exceptions.NoSuchKey:
            print(f"Incident not found: {incident_id}")
            return None
        except Exception as e:
            print(f"Error retrieving incident: {e}")
            return None