import enum


class StaffRole(str, enum.Enum):
    master = "master"
    manager = "manager"
    admin = "admin"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    canceled = "canceled"


class RescheduleRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

