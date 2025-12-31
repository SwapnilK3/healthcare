from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404

from core.utils import Pagination, rest_api_formatter
from .models import DoctorProfile, PatientProfile, PatientDoctorAssignment, UserRole
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    DoctorProfileSerializer, DoctorProfileListSerializer,
    DoctorCreateSerializer, DoctorUpdateSerializer,
    PatientProfileSerializer, PatientProfileListSerializer,
    PatientCreateSerializer, PatientUpdateSerializer,
    AssignmentSerializer, AssignmentCreateSerializer, PatientDoctorsSerializer
)

User = get_user_model()


class RegisterView(APIView):
    """API view for user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return rest_api_formatter(
                status_code=status.HTTP_201_CREATED,
                success=True,
                message='User registered successfully',
                data={
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                },
            )
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_code='VALIDATION_ERROR',
            error_message='Invalid input data',
            error_fields=list(serializer.errors.keys())
        )


class LoginView(APIView):
    """API view for user login."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, email=email, password=password)

            if user is not None:
                if not user.is_active:
                    return rest_api_formatter(
                        data=None,
                        status_code=status.HTTP_403_FORBIDDEN,
                        success=False,
                        message='User account is disabled',
                        error_code='ACCOUNT_DISABLED',
                        error_message='User account is disabled'
                    )

                refresh = RefreshToken.for_user(user)
                return rest_api_formatter(
                    data={
                        'user': UserSerializer(user).data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    },
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Login successful'
                )

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_401_UNAUTHORIZED,
                success=False,
                message='Invalid email or password',
                error_code='INVALID_CREDENTIALS',
                error_message='Invalid email or password'
            )

        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_code='VALIDATION_ERROR',
            error_message='Invalid input data',
            error_fields=list(serializer.errors.keys())
        )


class DoctorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Doctor CRUD operations.
    Provides list, create, retrieve, update, partial_update, destroy actions.
    """
    permission_classes = [IsAuthenticated]
    queryset = DoctorProfile.objects.select_related('user').all()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DoctorCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DoctorUpdateSerializer
        elif self.action == 'list':
            return DoctorProfileListSerializer
        return DoctorProfileSerializer

    def get_queryset(self):
        """Return active doctors only."""
        return self.queryset.filter(is_active=True).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """GET /doctors/ - List all active doctors."""
        queryset = self.get_queryset()
        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Doctors retrieved successfully'
        )

    def create(self, request, *args, **kwargs):
        """POST /doctors/ - Create a new doctor (User + DoctorProfile)."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return rest_api_formatter(
            data={'doctor': DoctorProfileSerializer(profile).data},
            status_code=status.HTTP_201_CREATED,
            success=True,
            message='Doctor created successfully'
        )

    def retrieve(self, request, *args, **kwargs):
        """GET /doctors/{id}/ - Get specific doctor details."""
        doctor = self.get_object()
        serializer = DoctorProfileSerializer(doctor)
        return rest_api_formatter(
            data={'doctor': serializer.data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Doctor retrieved successfully'
        )

    def update(self, request, *args, **kwargs):
        """PUT /doctors/{id}/ - Full update of doctor."""
        doctor = self.get_object()

        # Permission check
        if doctor.created_by != request.user and doctor.user != request.user:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_403_FORBIDDEN,
                success=False,
                message='You do not have permission to update this doctor',
                error_code='PERMISSION_DENIED',
                error_message='You do not have permission to update this doctor'
            )

        serializer = self.get_serializer(doctor, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return rest_api_formatter(
            data={'doctor': DoctorProfileSerializer(doctor).data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Doctor updated successfully'
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH /doctors/{id}/ - Partial update of doctor."""
        doctor = self.get_object()

        # Permission check
        if doctor.created_by != request.user and doctor.user != request.user:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_403_FORBIDDEN,
                success=False,
                message='You do not have permission to update this doctor',
                error_code='PERMISSION_DENIED',
                error_message='You do not have permission to update this doctor'
            )

        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return rest_api_formatter(
            data={'doctor': DoctorProfileSerializer(doctor).data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Doctor updated successfully'
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE /doctors/{id}/ - Soft delete a doctor."""
        doctor = self.get_object()

        # Permission check
        if doctor.created_by != request.user:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_403_FORBIDDEN,
                success=False,
                message='You do not have permission to delete this doctor',
                error_code='PERMISSION_DENIED',
                error_message='You do not have permission to delete this doctor'
            )

        # Soft delete both profile and user
        doctor.soft_delete()
        doctor.user.is_active = False
        doctor.user.save(update_fields=['is_active'])

        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
            success=True,
            message='Doctor deleted successfully'
        )

    @action(detail=False, methods=['get'])
    def available(self, request):
        """GET /doctors/available/ - Get only available doctors."""
        queryset = self.get_queryset().filter(is_available=True)
        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = DoctorProfileListSerializer(paginated_queryset, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Available doctors retrieved successfully'
        )

class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient CRUD operations.
    Provides list, create, retrieve, update, partial_update, destroy actions.
    """
    permission_classes = [IsAuthenticated]
    queryset = PatientProfile.objects.select_related('user').all()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return PatientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PatientUpdateSerializer
        elif self.action == 'list':
            return PatientProfileListSerializer
        return PatientProfileSerializer

    def get_queryset(self):
        """Return active patients created by authenticated user."""
        return self.queryset.filter(
            is_active=True,
            created_by=self.request.user
        ).order_by('-created_at')

    def list(self, request):
        """GET /patients/ - List all active patients."""
        queryset = self.get_queryset()
        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patients retrieved successfully'
        )

    def create(self, request):
        """POST /patients/ - Create a new patient (User + PatientProfile)."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return rest_api_formatter(
            data={'patient': PatientProfileSerializer(profile).data},
            status_code=status.HTTP_201_CREATED,
            success=True,
            message='Patient created successfully'
        )

    def retrieve(self, request, *args, **kwargs):
        """GET /patients/{id}/ - Get specific patient details."""
        patient = self.get_object()
        serializer = PatientProfileSerializer(patient)
        return rest_api_formatter(
            data={'patient': serializer.data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patient retrieved successfully'
        )

    def update(self, request, *args, **kwargs):
        """PUT /patients/{id}/ - Full update of patient."""
        patient = self.get_object()
        serializer = self.get_serializer(patient, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return rest_api_formatter(
            data={'patient': PatientProfileSerializer(patient).data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patient updated successfully'
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH /patients/{id}/ - Partial update of patient."""
        patient = self.get_object()
        serializer = self.get_serializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return rest_api_formatter(
            data={'patient': PatientProfileSerializer(patient).data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patient updated successfully'
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE /patients/{id}/ - Soft delete a patient."""
        patient = self.get_object()

        # Soft delete both profile and user
        patient.soft_delete()
        patient.user.is_active = False
        patient.user.save(update_fields=['is_active'])

        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
            success=True,
            message='Patient deleted successfully'
        )

    @action(detail=True, methods=['get'])
    def doctors(self, request, *args, **kwargs):
        """GET /patients/{id}/doctors/ - Get all doctors assigned to this patient."""
        patient = self.get_object()
        assignments = PatientDoctorAssignment.objects.filter(
            patient=patient.user,
            is_active=True
        ).select_related('doctor', 'doctor__doctor_profile')
        paginator = Pagination()
        paginated_assignments = paginator.paginate_queryset(assignments, request)
        serializer = PatientDoctorsSerializer(paginated_assignments, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        paginated_data['patient'] = patient.user.name
        paginated_data['patient_id'] = str(patient.user.id)
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patient doctors retrieved successfully'
        )


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient-Doctor Assignment (Mapping) operations.
    Provides complete CRUD for managing patient-doctor relationships.
    """
    permission_classes = [IsAuthenticated]
    queryset = PatientDoctorAssignment.objects.select_related(
        'patient', 'doctor', 'patient__patient_profile', 'doctor__doctor_profile'
    ).all()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def get_queryset(self):
        """Return active assignments."""
        return self.queryset.filter(is_active=True).order_by('-created_at')

    def list(self, request):
        """GET /mappings/ - List all active mappings."""
        queryset = self.get_queryset()
        paginator = Pagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Mappings retrieved successfully'
        )

    def create(self, request):
        """POST /mappings/ - Create a new patient-doctor mapping."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(created_by=request.user)
        return rest_api_formatter(
            data={'mapping': AssignmentSerializer(assignment).data},
            status_code=status.HTTP_201_CREATED,
            success=True,
            message='Doctor assigned to patient successfully'
        )

    def retrieve(self, request, *args, **kwargs):
        """GET /mappings/{id}/ - Get specific mapping details."""
        assignment = self.get_object()
        serializer = self.get_serializer(assignment)
        return rest_api_formatter(
            data={'mapping': serializer.data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Mapping retrieved successfully'
        )

    def update(self, request, *args, **kwargs):
        """PUT /mappings/{id}/ - Update mapping notes."""
        assignment = self.get_object()

        # Only creator can update
        if assignment.created_by != request.user:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_403_FORBIDDEN,
                success=False,
                message='You do not have permission to update this mapping',
                error_code='PERMISSION_DENIED',
                error_message='You do not have permission to update this mapping'
            )

        # Only allow updating notes
        if 'notes' in request.data:
            assignment.notes = request.data['notes']
            assignment.save()

        serializer = self.get_serializer(assignment)
        return rest_api_formatter(
            data={'mapping': serializer.data},
            status_code=status.HTTP_200_OK,
            success=True,
            message='Mapping updated successfully'
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH /mappings/{id}/ - Partially update mapping."""
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """DELETE /mappings/{id}/ - Soft delete a mapping."""
        assignment = self.get_object()

        # Only creator can delete
        if assignment.created_by != request.user:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_403_FORBIDDEN,
                success=False,
                message='You do not have permission to delete this mapping',
                error_code='PERMISSION_DENIED',
                error_message='You do not have permission to delete this mapping'
            )

        assignment.soft_delete()
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
            success=True,
            message='Doctor removed from patient successfully'
        )

    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def patient_mappings(self, request, patient_id=None):
        """GET /mappings/patient/{patient_id}/ - Get all doctors assigned to a specific patient."""
        patient = get_object_or_404(User, pk=patient_id, role=UserRole.PATIENT, is_active=True)
        assignments = self.get_queryset().filter(patient=patient)
        paginator = Pagination()
        paginated_assignments = paginator.paginate_queryset(assignments, request)
        serializer = PatientDoctorsSerializer(paginated_assignments, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        paginated_data['patient'] = patient.name
        paginated_data['patient_id'] = str(patient.id)
        return rest_api_formatter(
            data=paginated_data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Patient mappings retrieved successfully'
        )
