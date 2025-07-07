from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, status
from typing import Optional, Union
from jose import JWTError

from auth.jwt_handler import decode_access_token


class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Union[HTTPAuthorizationCredentials, None]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)

        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ugyldigt autentificeringsskema."
                )

            try:
                payload = decode_access_token(credentials.credentials)
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token kunne ikke dekodes."
                )

            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ugyldig eller udløbet token."
                )

            request.state.user = payload  # Gem data i request.state
            return credentials

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autentificering mislykkedes."
        )
