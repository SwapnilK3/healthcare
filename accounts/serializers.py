from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .models import DoctorProfile, PatientProfile, PatientDoctorAssignment, UserRole

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details (used in responses)."""

    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'phone', 'date_of_birth',
            'gender', 'address', 'role', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing users."""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(source='name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'full_name', 'role', 'is_active', 'created_at')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration (creates patient by default)."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.PATIENT,
        required=False
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'phone', 'date_of_birth',
            'gender', 'address', 'role', 'password', 'password_confirm'
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.get('role', UserRole.PATIENT)

        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            phone=validated_data.get('phone'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            address=validated_data.get('address'),
            role=role
        )

        # Auto-create profile based on role
        # Note: Only create patient profile if role is PATIENT
        # Admin users don't need profiles
        if role == UserRole.PATIENT:
            PatientProfile.objects.create(user=user, created_by=user)
        elif role == UserRole.DOCTOR:
            # Doctor profiles should be created via the doctor creation endpoint
            pass
        # Admin users don't get any profile

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class DoctorProfileSerializer(serializers.ModelSerializer):
    """Serializer for DoctorProfile with user details."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user = UserSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    created_by = serializers.ReadOnlyField(source='created_by.email')

    class Meta:
        model = DoctorProfile
        fields = (
            'id', 'user_id', 'user', 'full_name', 'specialization', 'license_number',
            'experience_years', 'is_available', 'is_active',
            'created_by', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user_id', 'created_by', 'created_at', 'updated_at')


class DoctorProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing doctors."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = DoctorProfile
        fields = (
            'id', 'user_id', 'name', 'email', 'phone', 'full_name',
            'specialization', 'is_available', 'is_active', 'created_at'
        )


class DoctorCreateSerializer(serializers.Serializer):
    """Serializer for creating a doctor (User + DoctorProfile)."""

    # User fields
    email = serializers.EmailField(required=True)
    name = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(max_length=17, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        required=False,
        allow_null=True
    )
    address = serializers.CharField(required=False, allow_blank=True)

    # Doctor profile fields
    specialization = serializers.CharField(max_length=100, required=True)
    license_number = serializers.CharField(max_length=50, required=True)
    experience_years = serializers.IntegerField(min_value=0, max_value=70, default=0)
    is_available = serializers.BooleanField(default=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value.lower()

    def validate_license_number(self, value):
        if DoctorProfile.objects.filter(license_number=value.upper()).exists():
            raise serializers.ValidationError("Doctor with this license number already exists.")
        return value.upper()

    @transaction.atomic
    def create(self, validated_data):
        # Extract profile data
        profile_data = {
            'specialization': validated_data.pop('specialization'),
            'license_number': validated_data.pop('license_number'),
            'experience_years': validated_data.pop('experience_years', 0),
            'is_available': validated_data.pop('is_available', True),
        }

        # Create user with doctor role
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            phone=validated_data.get('phone'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            address=validated_data.get('address'),
            role=UserRole.DOCTOR
        )

        # Create doctor profile
        profile = DoctorProfile.objects.create(
            user=user,
            created_by=self.context['request'].user,
            **profile_data
        )

        return profile


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating doctor profile."""

    # User fields (partial update)
    name = serializers.CharField(source='user.name', required=False)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False, allow_null=True)
    gender = serializers.ChoiceField(
        source='user.gender',
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        required=False,
        allow_null=True
    )
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)

    class Meta:
        model = DoctorProfile
        fields = (
            'name', 'phone', 'date_of_birth', 'gender', 'address',
            'specialization', 'license_number', 'experience_years', 'is_available'
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update user fields
        user_data = validated_data.pop('user', {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class PatientProfileSerializer(serializers.ModelSerializer):
    """Serializer for PatientProfile with user details."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.name', read_only=True)
    created_by = serializers.ReadOnlyField(source='created_by.email')

    class Meta:
        model = PatientProfile
        fields = (
            'id', 'user_id', 'user', 'full_name', 'blood_group', 'medical_history',
            'emergency_contact', 'allergies', 'is_active',
            'created_by', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user_id', 'created_by', 'created_at', 'updated_at')


class PatientProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing patients."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    full_name = serializers.CharField(source='user.name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            'id', 'user_id', 'name', 'full_name', 'email', 'phone',
            'date_of_birth', 'gender', 'blood_group', 'is_active', 'created_at'
        )


class PatientCreateSerializer(serializers.Serializer):
    """Serializer for creating a patient (User + PatientProfile)."""

    # User fields
    email = serializers.EmailField(required=True)
    name = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(max_length=17, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        required=False,
        allow_null=True
    )
    address = serializers.CharField(required=False, allow_blank=True)

    # Patient profile fields
    blood_group = serializers.ChoiceField(
        choices=[
            ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-'),
        ],
        required=False,
        allow_null=True
    )
    medical_history = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(max_length=17, required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value.lower()

    @transaction.atomic
    def create(self, validated_data):
        # Extract profile data
        profile_data = {
            'blood_group': validated_data.pop('blood_group', None),
            'medical_history': validated_data.pop('medical_history', ''),
            'emergency_contact': validated_data.pop('emergency_contact', ''),
            'allergies': validated_data.pop('allergies', ''),
        }

        # Create user with patient role
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            phone=validated_data.get('phone'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            address=validated_data.get('address'),
            role=UserRole.PATIENT
        )

        # Create patient profile
        profile = PatientProfile.objects.create(
            user=user,
            created_by=self.context['request'].user,
            **profile_data
        )

        return profile


class PatientUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating patient profile."""

    # User fields (partial update)
    name = serializers.CharField(source='user.name', required=False)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False, allow_null=True)
    gender = serializers.ChoiceField(
        source='user.gender',
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        required=False,
        allow_null=True
    )
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)

    class Meta:
        model = PatientProfile
        fields = (
            'name', 'phone', 'date_of_birth', 'gender', 'address',
            'blood_group', 'medical_history', 'emergency_contact', 'allergies'
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update user fields
        user_data = validated_data.pop('user', {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class AssignmentSerializer(serializers.ModelSerializer):
    """Serializer for PatientDoctorAssignment with full details."""

    id = serializers.UUIDField(read_only=True)
    patient_details = UserListSerializer(source='patient', read_only=True)
    doctor_details = UserListSerializer(source='doctor', read_only=True)
    created_by = serializers.ReadOnlyField(source='created_by.email')

    class Meta:
        model = PatientDoctorAssignment
        fields = (
            'id', 'patient', 'doctor', 'patient_details', 'doctor_details',
            'notes', 'assigned_date', 'is_active',
            'created_by', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'assigned_date', 'created_by', 'created_at', 'updated_at')

    def validate_patient(self, value):
        if value.role != UserRole.PATIENT:
            raise serializers.ValidationError("Selected user is not a patient.")
        return value

    def validate_doctor(self, value):
        if value.role != UserRole.DOCTOR:
            raise serializers.ValidationError("Selected user is not a doctor.")
        return value

    def validate(self, attrs):
        patient = attrs.get('patient')
        doctor = attrs.get('doctor')

        if self.instance is None:  # Only on create
            if PatientDoctorAssignment.objects.filter(
                patient=patient, doctor=doctor, is_active=True
            ).exists():
                raise serializers.ValidationError({
                    'error': 'This patient is already assigned to this doctor.'
                })
        return attrs


class AssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assignments."""

    class Meta:
        model = PatientDoctorAssignment
        fields = ('patient', 'doctor', 'notes')

    def validate_patient(self, value):
        if value.role != UserRole.PATIENT:
            raise serializers.ValidationError("Selected user is not a patient.")
        return value

    def validate_doctor(self, value):
        if value.role != UserRole.DOCTOR:
            raise serializers.ValidationError("Selected user is not a doctor.")
        return value

    def validate(self, attrs):
        patient = attrs.get('patient')
        doctor = attrs.get('doctor')

        if PatientDoctorAssignment.objects.filter(
            patient=patient, doctor=doctor, is_active=True
        ).exists():
            raise serializers.ValidationError({
                'error': 'This patient is already assigned to this doctor.'
            })
        return attrs


class PatientDoctorsSerializer(serializers.ModelSerializer):
    """Serializer for getting doctors assigned to a patient."""

    id = serializers.UUIDField(read_only=True)
    doctor = UserListSerializer(read_only=True)
    doctor_profile = DoctorProfileListSerializer(source='doctor.doctor_profile', read_only=True)

    class Meta:
        model = PatientDoctorAssignment
        fields = ('id', 'doctor', 'doctor_profile', 'notes', 'assigned_date', 'is_active')

