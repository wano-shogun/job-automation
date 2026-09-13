"""Pydantic models for user profile and answers."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Profile(BaseModel):
    """User profile data for job applications."""

    # Basic info
    name: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: EmailStr
    phone: str

    # Professional info
    linkedIn: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = "United States"

    # Resume (file path)
    resume: Optional[str] = None

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "555-123-4567",
                "linkedIn": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "portfolio": "https://johndoe.com",
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
                "country": "United States",
                "resume": "/path/to/resume.pdf",
            }
        }


class Answers(BaseModel):
    """Common answers to job application questions."""

    class Config:
        """Allow arbitrary fields for flexible Q&A."""

        extra = "allow"

    # Example fields that might be asked
    whyInterested: Optional[str] = Field(
        None, description="Why are you interested in this role?"
    )
    whyCompany: Optional[str] = Field(None, description="Why do you want to work at this company?")
    experience: Optional[str] = Field(None, description="Relevant experience for the role")
    availability: Optional[str] = Field(None, description="When can you start?")
    workAuthorization: Optional[str] = Field(None, description="Are you authorized to work in the US?")
    sponsorship: Optional[str] = Field(
        None, description="Do you require sponsorship?"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "whyInterested": "I'm excited about the opportunity to work with cutting-edge technology...",
                "whyCompany": "Your company's mission aligns with my values...",
                "experience": "I have 5+ years of experience in...",
                "availability": "2 weeks",
                "workAuthorization": "Yes, I'm a US citizen",
                "sponsorship": "No, I don't require sponsorship",
                "customQuestion1": "Custom answer here",
            }
        }
