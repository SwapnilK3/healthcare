from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404

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
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                    return Response({
                        'error': 'User account is disabled'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': 'Invalid email or password'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    
    def list(self, request):
        """GET /doctors/ - List all active doctors."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'doctors': serializer.data
        })
    
    def create(self, request):
        """POST /doctors/ - Create a new doctor (User + DoctorProfile)."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response({
            'message': 'Doctor created successfully',
            'doctor': DoctorProfileSerializer(profile).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, pk=None):
        """GET /doctors/{id}/ - Get specific doctor details."""
        doctor = self.get_object()
        serializer = DoctorProfileSerializer(doctor)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /doctors/{id}/ - Full update of doctor."""
        doctor = self.get_object()
        
        # Permission check
        if doctor.created_by != request.user and doctor.user != request.user:
            return Response({
                'error': 'You do not have permission to update this doctor'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(doctor, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Doctor updated successfully',
            'doctor': DoctorProfileSerializer(doctor).data
        })
    
    def partial_update(self, request, pk=None):
        """PATCH /doctors/{id}/ - Partial update of doctor."""
        doctor = self.get_object()
        
        # Permission check
        if doctor.created_by != request.user and doctor.user != request.user:
            return Response({
                'error': 'You do not have permission to update this doctor'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Doctor updated successfully',
            'doctor': DoctorProfileSerializer(doctor).data
        })
    
    def destroy(self, request, pk=None):
        """DELETE /doctors/{id}/ - Soft delete a doctor."""
        doctor = self.get_object()
        
        # Permission check
        if doctor.created_by != request.user:
            return Response({
                'error': 'You do not have permission to delete this doctor'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Soft delete both profile and user
        doctor.soft_delete()
        doctor.user.is_active = False
        doctor.user.save(update_fields=['is_active'])
        
        return Response({
            'message': 'Doctor deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """GET /doctors/available/ - Get only available doctors."""
        queryset = self.get_queryset().filter(is_available=True)
        serializer = DoctorProfileListSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'doctors': serializer.data
        })


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
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'patients': serializer.data
        })
    
    def create(self, request):
        """POST /patients/ - Create a new patient (User + PatientProfile)."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response({
            'message': 'Patient created successfully',
            'patient': PatientProfileSerializer(profile).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, pk=None):
        """GET /patients/{id}/ - Get specific patient details."""
        patient = self.get_object()
        serializer = PatientProfileSerializer(patient)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /patients/{id}/ - Full update of patient."""
        patient = self.get_object()
        serializer = self.get_serializer(patient, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Patient updated successfully',
            'patient': PatientProfileSerializer(patient).data
        })
    
    def partial_update(self, request, pk=None):
        """PATCH /patients/{id}/ - Partial update of patient."""
        patient = self.get_object()
        serializer = self.get_serializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Patient updated successfully',
            'patient': PatientProfileSerializer(patient).data
        })
    
    def destroy(self, request, pk=None):
        """DELETE /patients/{id}/ - Soft delete a patient."""
        patient = self.get_object()
        
        # Soft delete both profile and user
        patient.soft_delete()
        patient.user.is_active = False
        patient.user.save(update_fields=['is_active'])
        
        return Response({
            'message': 'Patient deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        """GET /patients/{id}/doctors/ - Get all doctors assigned to this patient."""
        patient = self.get_object()
        assignments = PatientDoctorAssignment.objects.filter(
            patient=patient.user,
            is_active=True
        ).select_related('doctor', 'doctor__doctor_profile')
        serializer = PatientDoctorsSerializer(assignments, many=True)
        return Response({
            'patient': patient.user.name,
            'patient_id': str(patient.user.id),
            'count': assignments.count(),
            'assigned_doctors': serializer.data
        })


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
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'mappings': serializer.data
        })
    
    def create(self, request):
        """POST /mappings/ - Create a new patient-doctor mapping."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(created_by=request.user)
        return Response({
            'message': 'Doctor assigned to patient successfully',
            'mapping': AssignmentSerializer(assignment).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, pk=None):
        """GET /mappings/{id}/ - Get specific mapping details."""
        assignment = self.get_object()
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /mappings/{id}/ - Update mapping notes."""
        assignment = self.get_object()
        
        # Only creator can update
        if assignment.created_by != request.user:
            return Response({
                'error': 'You do not have permission to update this mapping'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow updating notes
        if 'notes' in request.data:
            assignment.notes = request.data['notes']
            assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response({
            'message': 'Mapping updated successfully',
            'mapping': serializer.data
        })
    
    def partial_update(self, request, pk=None):
        """PATCH /mappings/{id}/ - Partially update mapping."""
        return self.update(request, pk)
    
    def destroy(self, request, pk=None):
        """DELETE /mappings/{id}/ - Soft delete a mapping."""
        assignment = self.get_object()
        
        # Only creator can delete
        if assignment.created_by != request.user:
            return Response({
                'error': 'You do not have permission to delete this mapping'
            }, status=status.HTTP_403_FORBIDDEN)
        
        assignment.soft_delete()
        return Response({
            'message': 'Doctor removed from patient successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def patient_mappings(self, request, patient_id=None):
        """GET /mappings/patient/{patient_id}/ - Get all doctors assigned to a specific patient."""
        patient = get_object_or_404(User, pk=patient_id, role=UserRole.PATIENT, is_active=True)
        assignments = self.get_queryset().filter(patient=patient)
        serializer = PatientDoctorsSerializer(assignments, many=True)
        return Response({
            'patient': patient.name,
            'patient_id': str(patient.id),
            'count': assignments.count(),
            'assigned_doctors': serializer.data
        })

