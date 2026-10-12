# from fastapi import HTTPException, status


# class AppException(HTTPException):
#     def __init__(self, status_code: int, detail: str):
#         super().__init__(status_code=status_code, detail=detail)


# class NotFoundError(AppException):
#     def __init__(self, resource: str = "Resource"):
#         super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found.")


# class ConflictError(AppException):
#     def __init__(self, detail: str = "Resource already exists."):
#         super().__init__(status.HTTP_409_CONFLICT, detail)


# class UnauthorizedError(AppException):
#     def __init__(self, detail: str = "Unauthorized."):
#         super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


# class ForbiddenError(AppException):
#     def __init__(self, detail: str = "Insufficient permissions."):
#         super().__init__(status.HTTP_403_FORBIDDEN, detail)


# class BadRequestError(AppException):
#     def __init__(self, detail: str = "Bad request."):
#         super().__init__(status.HTTP_400_BAD_REQUEST, detail)


# class TenantNotFoundError(AppException):
#     def __init__(self):
#         super().__init__(status.HTTP_403_FORBIDDEN, "Tenant not found or inactive.")


from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found.")


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource already exists."):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Unauthorized."):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Insufficient permissions."):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad request."):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class TenantNotFoundError(AppException):
    def __init__(self, message: str = "Tenant not found or inactive."):
        # FIX BUG-006: was HTTP_403_FORBIDDEN — changed to 400 Bad Request
        # because a missing/invalid tenant header is a client input error,
        # not an authorization failure.
        super().__init__(status.HTTP_400_BAD_REQUEST, message)


class ValidationError(AppException):
    def __init__(self, detail: str = "Invalid data provided."):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)