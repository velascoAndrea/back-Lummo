import logging

logger = logging.getLogger("lummo.email")


def send_results_email(
    to_email: str,
    nombre: str,
    nivel_global: str,
    puntaje_global: float,
    token_reporte: str,
    password_temporal: str = None,
):
    """MVP stub: imprime el email en consola en lugar de enviarlo."""
    report_url = f"http://localhost:3000/results?token={token_reporte}"
    lines = [
        "=" * 60,
        "📧 EMAIL (stub — no enviado)",
        f"Para:    {to_email}",
        f"Asunto: Tus resultados del diagnóstico LUMMO están listos",
        "",
        f"Hola {nombre},",
        "",
        f"Tu diagnóstico está completo.",
        f"Nivel global: {nivel_global.upper()}  |  Puntaje: {puntaje_global:.1f}%",
        "",
        f"Ver tu reporte completo:",
        f"{report_url}",
    ]
    if password_temporal:
        lines += [
            "",
            "Tu cuenta fue creada automáticamente.",
            f"Correo:     {to_email}",
            f"Contraseña temporal: {password_temporal}",
            "Cambia tu contraseña al iniciar sesión.",
        ]
    lines.append("=" * 60)
    logger.info("\n".join(lines))
    print("\n".join(lines))
