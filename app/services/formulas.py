def calculate_bmr(weight, height, age, gender="male"):
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161


def water_target_ml(weight):
    return weight * 35


def protein_target_g(weight):
    return weight * 1.2
