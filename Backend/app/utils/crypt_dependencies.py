import bcrypt

def crypt_password(password):
    """
    Hashea una contraseña utilizando bcrypt.
    
    Args:
        password (str): Contraseña a hashear.
    
    Returns:
        str: Contraseña hasheada.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def crypt_verify_password(password, hashed_password):
    """
    Verifica si una contraseña coincide con la hasheada.
    
    Args:
        password (str): Contraseña a verificar.
        hashed_password (str): Contraseña hasheada.
        
    Returns:
        bool: True si la contraseña coincide, False si no.
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
