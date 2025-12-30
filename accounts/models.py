from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator, MinValueValidator, MaxValueValidator

from core.models import AbstractUUID, AbstractMonitor, AbstractBaseModel


class UserRole(models.TextChoices):
    """Available roles for users in the system."""
    ADMIN = 'admin', 'Admin'
    DOCTOR = 'doctor', 'Doctor'
    PATIENT = 'patient', 'Patient'


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not name:
            raise ValueError('The Name field must be set')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, name=name.strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be 9-15 digits. Can start with + or country code."
)


class User(AbstractBaseUser, PermissionsMixin, AbstractUUID, AbstractMonitor):
    """
    Custom User model with UUID primary key and role-based access.
    Contains common fields for all user types (admin, doctor, patient).
    Role-specific data is stored in DoctorProfile or PatientProfile.
    
    Inherits from:
    - AbstractUUID: UUID primary key
    - AbstractMonitor: created_at, updated_at timestamps
    """
    # Authentication
    email = models.EmailField(unique=True, db_index=True)
    
    # Common User Info
    name = models.CharField(max_length=255, validators=[MinLengthValidator(2)])
    phone = models.CharField(max_length=17, validators=[phone_regex], blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True,
        null=True
    )
    address = models.TextField(blank=True, null=True)
    
    # Role
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.PATIENT,
        db_index=True
    )
    
    # Status (using is_active from Django's auth, not AbstractActive)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        self.name = ' '.join(self.name.strip().split())
        super().save(*args, **kwargs)


class DoctorProfile(AbstractBaseModel):
    """
    Profile containing doctor-specific information.
    Links to User model via OneToOne relationship.
    
    Inherits from AbstractBaseModel:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (is_active)
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        limit_choices_to={'role': UserRole.DOCTOR}
    )
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    experience_years = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(70)]
    )
    is_available = models.BooleanField(default=True)
    
    # Created by (admin who created this profile)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_doctor_profiles'
    )

    class Meta:
        db_table = 'doctor_profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['specialization']),
            models.Index(fields=['license_number']),
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return f"Dr. {self.user.name} - {self.specialization}"

    @property
    def full_name(self):
        return f"Dr. {self.user.name}"

    def save(self, *args, **kwargs):
        self.license_number = self.license_number.upper().strip()
        self.specialization = self.specialization.strip()
        super().save(*args, **kwargs)


class PatientProfile(AbstractBaseModel):
    """
    Profile containing patient-specific information.
    Links to User model via OneToOne relationship.
    
    Inherits from AbstractBaseModel:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (is_active)
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        limit_choices_to={'role': UserRole.PATIENT}
    )
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-'),
        ],
        blank=True,
        null=True
    )
    medical_history = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(
        max_length=17,
        validators=[phone_regex],
        blank=True,
        null=True
    )
    allergies = models.TextField(blank=True, null=True)
    
    # Created by (admin who created this profile)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_patient_profiles'
    )

    class Meta:
        db_table = 'patient_profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"Patient: {self.user.name}"


class PatientDoctorAssignment(AbstractBaseModel):
    """
    Represents the assignment/mapping between a patient and a doctor.
    
    Inherits from AbstractBaseModel:
    - UUID primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (is_active)
    """
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_assignments',
        limit_choices_to={'role': UserRole.PATIENT}
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patient_assignments',
        limit_choices_to={'role': UserRole.DOCTOR}
    )
    notes = models.TextField(blank=True, null=True)
    assigned_date = models.DateField(auto_now_add=True)
    
    # Created by (admin who created this assignment)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assignments'
    )

    class Meta:
        db_table = 'patient_doctor_assignments'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['patient', 'doctor'],
                condition=models.Q(is_active=True),
                name='unique_active_patient_doctor_assignment'
            )
        ]
        indexes = [
            models.Index(fields=['patient', 'doctor']),
            models.Index(fields=['assigned_date']),
        ]

    def __str__(self):
        return f"{self.patient.name} -> Dr. {self.doctor.name}"


